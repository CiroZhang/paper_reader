import os
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from weights_utils import ensure_yolo_weights
from pdf_extractor import export_pdfs_to_mds

APP_TITLE = "PDF → Markdown (DocLayNet YOLO) GUI"
DEFAULT_WEIGHTS = "yolo_model/doclaynet.pt"
HF_REPO_ID = "malaysia-ai/YOLOv8X-DocLayNet-Full-1024-42"
HF_REPO_FILE = "weights/best.pt"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("840x560")

        self.input_dirs = []
        self.output_dir = os.path.abspath("outputs")
        self.save_raw_json = tk.BooleanVar(value=False)
        self.save_removed  = tk.BooleanVar(value=False)
        self.prefer_cli    = tk.BooleanVar(value=True)
        self.weights_path  = tk.StringVar(value=DEFAULT_WEIGHTS)
        self.log_queue = queue.Queue()
        self._build_ui()
        self.after(100, self._drain_log_queue)
        self.stop_flag = threading.Event()

    def _build_ui(self):
        top = tk.Frame(self); top.pack(fill="x", padx=12, pady=8)

        tk.Label(top, text="Input Folders (each contains PDFs):", font=("Helvetica", 11, "bold")).pack(anchor="w")
        mid = tk.Frame(self); mid.pack(fill="x", padx=12)
        self.listbox = tk.Listbox(mid, height=6, selectmode=tk.EXTENDED)
        self.listbox.pack(side="left", fill="both", expand=True)

        btns = tk.Frame(mid); btns.pack(side="left", padx=8)
        tk.Button(btns, text="Add Folder…", command=self._add_folder).pack(fill="x", pady=2)
        tk.Button(btns, text="Remove Selected", command=self._remove_selected).pack(fill="x", pady=2)
        tk.Button(btns, text="Clear", command=self._clear_all).pack(fill="x", pady=2)

        opt = tk.LabelFrame(self, text="Options"); opt.pack(fill="x", padx=12, pady=8)

        out_row = tk.Frame(opt); out_row.pack(fill="x", pady=4)
        tk.Label(out_row, text="Output Folder:").pack(side="left")
        self.out_entry = tk.Entry(out_row); self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.out_entry.insert(0, self.output_dir)
        tk.Button(out_row, text="Choose…", command=self._choose_output).pack(side="left")

        wt_row = tk.Frame(opt); wt_row.pack(fill="x", pady=4)
        tk.Label(wt_row, text="YOLO Weights:").pack(side="left")
        self.wt_entry = tk.Entry(wt_row); self.wt_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.wt_entry.insert(0, self.weights_path.get())
        tk.Button(wt_row, text="Browse…", command=self._choose_weights).pack(side="left")
        tk.Button(wt_row, text="Auto-Download (if missing)", command=self._ensure_weights).pack(side="left", padx=6)

        cb_row = tk.Frame(opt); cb_row.pack(fill="x", pady=4)
        tk.Checkbutton(cb_row, text="Save raw JSONL", variable=self.save_raw_json).pack(side="left")
        tk.Checkbutton(cb_row, text="Save removed sections", variable=self.save_removed).pack(side="left")
        tk.Checkbutton(cb_row, text="Prefer huggingface-cli", variable=self.prefer_cli).pack(side="left", padx=12)

        run_bar = tk.Frame(self); run_bar.pack(fill="x", padx=12, pady=8)
        self.run_btn = tk.Button(run_bar, text="Run Pipeline", height=2, command=self._on_run)
        self.run_btn.pack(side="left")
        self.stop_btn = tk.Button(run_bar, text="Stop", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        tk.Label(self, text="Log:").pack(anchor="w", padx=12)
        self.log = ScrolledText(self, height=12, state="normal")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0,12))

        try:
            from tkinterdnd2 import DND_FILES  # noqa: F401
            self._log("Drag-and-drop available (tkinterdnd2 installed).")
        except Exception:
            self._log("Drag-and-drop not enabled (install tkinterdnd2 to enable).")

    def _add_folder(self):
        d = filedialog.askdirectory(title="Choose input folder (contains PDFs)")
        if d:
            d = os.path.abspath(d)
            if d not in self.input_dirs:
                self.input_dirs.append(d)
                self.listbox.insert(tk.END, d)

    def _remove_selected(self):
        sel = list(self.listbox.curselection())[::-1]
        for idx in sel:
            path = self.listbox.get(idx)
            self.listbox.delete(idx)
            if path in self.input_dirs:
                self.input_dirs.remove(path)

    def _clear_all(self):
        self.listbox.delete(0, tk.END)
        self.input_dirs.clear()

    def _choose_output(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.output_dir = os.path.abspath(d)
            self.out_entry.delete(0, tk.END)
            self.out_entry.insert(0, self.output_dir)

    def _choose_weights(self):
        f = filedialog.askopenfilename(
            title="Choose YOLO weights .pt",
            filetypes=[("PyTorch weights", "*.pt"), ("All files", "*.*")]
        )
        if f:
            self.weights_path.set(os.path.abspath(f))
            self.wt_entry.delete(0, tk.END)
            self.wt_entry.insert(0, self.weights_path.get())

    def _ensure_weights(self):
        path = self.wt_entry.get().strip() or DEFAULT_WEIGHTS
        self.weights_path.set(path)
        try:
            self._log(f"[weights] ensuring → {path}")
            ensure_yolo_weights(
                weights_path=path,
                repo_id=HF_REPO_ID,
                repo_file=HF_REPO_FILE,
                prefer_cli=self.prefer_cli.get(),
            )
            self._log("[weights] OK")
        except Exception as e:
            messagebox.showerror("Weights error", str(e))
            self._log(f"[weights] ERROR: {e}")

    def _on_run(self):
        if not self.input_dirs:
            messagebox.showwarning("No input", "Add at least one input folder.")
            return
        self.output_dir = self.out_entry.get().strip() or os.path.abspath("outputs")
        self.weights_path.set(self.wt_entry.get().strip() or DEFAULT_WEIGHTS)

        try:
            ensure_yolo_weights(
                weights_path=self.weights_path.get(),
                repo_id=HF_REPO_ID,
                repo_file=HF_REPO_FILE,
                prefer_cli=self.prefer_cli.get(),
            )
        except Exception as e:
            messagebox.showerror("Weights error", str(e))
            return

        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._log("=== Pipeline started ===")
        self.stop_flag.clear()
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    def _on_stop(self):
        self.stop_flag.set()
        self._log("[stop] Requested. Finishing current file…")

    def _worker(self):
        try:
            for i, in_dir in enumerate(self.input_dirs, start=1):
                if self.stop_flag.is_set():
                    self._log("[stop] Aborting remaining jobs.")
                    break
                dataset_name = os.path.basename(in_dir.rstrip(os.sep)) or f"job_{i}"
                out_name = os.path.join(self.output_dir, dataset_name)

                self._log(f"[run] {i}/{len(self.input_dirs)} → input='{in_dir}'  out='{out_name}'")
                failed = export_pdfs_to_mds(
                    input_folder=in_dir,
                    output_folder=out_name,
                    save_raw_json=self.save_raw_json.get(),
                    save_removed=self.save_removed.get(),
                )
                if failed:
                    self._log(f"[warn] failed files:\n  - " + "\n  - ".join(map(str, failed)))
                else:
                    self._log("[ok] completed without failures")

            self._log("=== Pipeline finished ===")
        except Exception as e:
            self._log(f"[error] {e}")
            messagebox.showerror("Run error", str(e))
        finally:
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _drain_log_queue(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log.insert(tk.END, line + "\n")
                self.log.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _log(self, msg: str):
        self.log_queue.put(msg)

if __name__ == "__main__":
    App().mainloop()

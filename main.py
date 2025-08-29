# main.py
import argparse
from weights_utils import ensure_yolo_weights
from pdf_extractor import export_pdfs_to_mds

def main():
    parser = argparse.ArgumentParser(description="PDF → Markdown pipeline")
    parser.add_argument("input_folder", help="Folder with PDFs")
    parser.add_argument("output_folder", help="Output/dataset folder name")
    parser.add_argument("--save-raw-json", action="store_true", default=False)
    parser.add_argument("--save-removed", action="store_true", default=False)
    parser.add_argument("--weights", default="yolo_model/doclaynet.pt",
                        help="Path to YOLO weights (will auto-download if missing).")
    parser.add_argument("--no-auto-download", action="store_true",
                        help="Disable auto-download behavior.")
    parser.add_argument("--prefer-cli", action="store_true", default=True,
                        help="Prefer using huggingface-cli if available (default: on).")
    parser.add_argument("--repo-id", default="malaysia-ai/YOLOv8X-DocLayNet-Full-1024-42")
    parser.add_argument("--repo-file", default="weights/best.pt")
    args = parser.parse_args()

    # Ensure weights exist (unless user opted out)
    if not args.no_auto_download:
        ensure_yolo_weights(
            weights_path=args.weights,
            repo_id=args.repo_id,
            repo_file=args.repo_file,
            prefer_cli=args.prefer_cli,
        )

    failed = export_pdfs_to_mds(
        args.input_folder,
        args.output_folder,
        save_raw_json=args.save_raw_json,
        save_removed=args.save_removed,
    )

    if failed:
        print("❌ Failed files:")
        for f in failed:
            print(" -", f)
    else:
        print("✅ Export completed successfully.")

if __name__ == "__main__":
    main()

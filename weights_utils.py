# weights_utils.py
import shutil, subprocess
from pathlib import Path

def _has_cmd(name: str) -> bool:
    from shutil import which
    return which(name) is not None

def ensure_yolo_weights(
    weights_path: str = "yolo_model/doclaynet.pt",
    repo_id: str = "malaysia-ai/YOLOv8X-DocLayNet-Full-1024-42",
    repo_file: str = "weights/best.pt",
    prefer_cli: bool = True,
) -> str:
    """
    Ensure YOLO weights exist at weights_path.
    Try huggingface-cli first (your exact flow), then huggingface_hub as fallback.
    """
    wp = Path(weights_path)
    wp.parent.mkdir(parents=True, exist_ok=True)
    if wp.exists():
        print(f"[INFO] Using existing weights: {wp}")
        return str(wp)

    print(f"[INFO] Weights missing → {wp}. Trying auto-download...")
    # Try your CLI path
    if prefer_cli and _has_cmd("huggingface-cli"):
        tmp = wp.parent / "_hf_tmp_weights"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["huggingface-cli", "download", repo_id, repo_file, "--local-dir", str(tmp)],
                check=True,
            )
            src = tmp / Path(repo_file).name
            if not src.exists():
                alt = tmp / repo_file
                src = alt if alt.exists() else src
            if not src.exists():
                raise FileNotFoundError(f"Downloaded file not found at {src}")
            shutil.move(str(src), str(wp))
            shutil.rmtree(tmp, ignore_errors=True)
            print(f"[INFO] Downloaded → {wp}")
            return str(wp)
        except Exception as e:
            print(f"[WARN] huggingface-cli failed: {e}")

    # Fallback: Python API
    print("[INFO] Falling back to huggingface_hub Python API...")
    try:
        from huggingface_hub import hf_hub_download
        downloaded = hf_hub_download(
            repo_id=repo_id, filename=repo_file,
            local_dir=str(wp.parent), local_dir_use_symlinks=False
        )
        if Path(downloaded) != wp:
            shutil.move(downloaded, str(wp))
        print(f"[INFO] Downloaded → {wp}")
        return str(wp)
    except Exception as e:
        raise RuntimeError(
            "Failed to download weights via both CLI and Python API. "
            "Check internet and repo/filename."
        ) from e

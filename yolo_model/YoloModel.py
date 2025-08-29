import fitz
from ultralytics import YOLO
from PIL import Image
from collections import defaultdict
from functools import lru_cache

RENDER_SCALE = 3.0
IMAGE_CLASSES = {"picture", "table", "formula"}
DEFAULT_WEIGHTS = "yolo_model/doclaynet.pt"

import warnings
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r"You are using `torch\.load` with `weights_only=False`"
)


@lru_cache(maxsize=1)
def get_model(weights_path: str = DEFAULT_WEIGHTS):
    # Lazy load on first use only
    return YOLO(weights_path)


def _iou(a, b):
    ax0, ay0, ax1, ay1 = a;
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0);
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0);
    inter = iw * ih
    if inter <= 0: return 0.0
    return inter / (((ax1 - ax0) * (ay1 - ay0)) + ((bx1 - bx0) * (by1 - by0)) - inter + 1e-9)


def _cfrac(a, b):
    ax0, ay0, ax1, ay1 = a;
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0);
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0);
    inter = iw * ih
    amin = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0))
    if amin <= 0: return 0.0
    return inter / (amin + 1e-9)


def _union(a, b):
    ax0, ay0, ax1, ay1 = a;
    bx0, by0, bx1, by1 = b
    return (min(ax0, bx0), min(ay0, by0), max(ax1, bx1), max(ay1, by1))


def _results_to_regs(res):
    n = res.names;
    out = []
    for b in res.boxes:
        x0, y0, x1, y1 = map(float, b.xyxy[0].tolist())
        out.append(
            {"c": str(n[int(b.cls)]).strip().lower(), "p": float(b.conf), "x0": x0, "y0": y0, "x1": x1, "y1": y1})
    return out


def merge_overlapping_same_class(regs, page, render_scale=3.0, iou_t=0.40, cont_t=0.85, eps=2.0):
    byc = {}
    for r in regs: byc.setdefault(r["c"], []).append(r)
    out = []
    for cls, arr in byc.items():
        arr = sorted(arr, key=lambda r: (-r["p"], r["x0"], r["y0"]))
        used = [False] * len(arr)
        for i in range(len(arr)):
            if used[i]: continue
            a = arr[i];
            x0, y0, x1, y1 = a["x0"], a["y0"], a["x1"], a["y1"];
            best = a["p"];
            used[i] = True
            ch = True
            while ch:
                ch = False
                for j in range(len(arr)):
                    if used[j]: continue
                    r = arr[j]
                    nd = (abs(r["x0"] - x0) <= eps and abs(r["y0"] - y0) <= eps and abs(r["x1"] - x1) <= eps and abs(
                        r["y1"] - y1) <= eps)
                    if nd or _iou((x0, y0, x1, y1), (r["x0"], r["y0"], r["x1"], r["y1"])) >= iou_t or _cfrac(
                            (x0, y0, x1, y1), (r["x0"], r["y0"], r["x1"], r["y1"])) >= cont_t:
                        x0, y0, x1, y1 = _union((x0, y0, x1, y1), (r["x0"], r["y0"], r["x1"], r["y1"]))
                        best = max(best, r["p"]);
                        used[j] = True;
                        ch = True
            out.append({"c": cls, "p": best, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
    return out


def sort_regions_interleaved(regs, page, render_scale=3.0, full_w=0.70, min_gap=0.12, band_pad=0.005):
    pw, ph = float(page.rect.width), float(page.rect.height)
    items = []
    for r in regs:
        x0, y0, x1, y1 = r["x0"] / render_scale, r["y0"] / render_scale, r["x1"] / render_scale, r["y1"] / render_scale
        items.append({"r": r, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "w": x1 - x0, "xc": 0.5 * (x0 + x1)})
    if not items: return []
    full = [it for it in items if it["w"] >= full_w * pw];
    col = [it for it in items if it["w"] < full_w * pw]
    full.sort(key=lambda it: (it["y0"], it["x0"]));
    pad = band_pad * ph
    cuts = [0.0]
    for f in full: cuts += [max(0.0, f["y0"] - pad), min(ph, f["y1"] + pad)]
    cuts.append(ph);
    segs = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]
    out = []
    for si, (yt, yb) in enumerate(segs):
        if yb - yt <= 0: continue
        if si % 2 == 1:
            seg = [f for f in full if f["y0"] >= yt and f["y1"] <= yb];
            seg.sort(key=lambda it: (it["y0"], it["x0"]))
            out += [it["r"] for it in seg]
        else:
            seg = [it for it in col if it["y0"] >= yt and it["y1"] <= yb]
            if not seg: continue
            seg.sort(key=lambda it: it["xc"])
            gv, gi = 0.0, 0
            for i in range(len(seg) - 1):
                g = seg[i + 1]["xc"] - seg[i]["xc"]
                if g > gv: gv, gi = g, i
            if gv >= min_gap * pw:
                L, R = seg[:gi + 1], seg[gi + 1:];
                L.sort(key=lambda it: (it["y0"], it["x0"]));
                R.sort(key=lambda it: (it["y0"], it["x0"]))
                out += [it["r"] for it in L] + [it["r"] for it in R]
            else:
                seg.sort(key=lambda it: (it["y0"], it["x0"]));
                out += [it["r"] for it in seg]
    return out


def get_yolo_output(pdf_name, pdf_path, output_path):
    model = get_model()
    out = []
    cnt = defaultdict(int)
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            mat = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            res = model.predict(im, conf=0.40, iou=0.10, agnostic_nms=True, verbose=False)[0]
            regs = _results_to_regs(res)
            regs = merge_overlapping_same_class(regs, page, render_scale=RENDER_SCALE, iou_t=0.40, cont_t=0.85, eps=2.0)
            regs = sort_regions_interleaved(regs, page, render_scale=RENDER_SCALE)
            for r in regs:
                pad = 6.0
                x0 = max(0, r["x0"] - pad);
                y0 = max(0, r["y0"] - pad)
                x1 = min(pix.width, r["x1"] + pad);
                y1 = min(pix.height, r["y1"] + pad)
                if r["c"] in IMAGE_CLASSES:
                    cnt[r["c"]] += 1
                    rel = f"{pdf_name}/p{pno:03d}_{r['c']}{cnt[r['c']]:02d}.png"
                    Image.frombytes("RGB", (pix.width, pix.height), pix.samples).crop((x0, y0, x1, y1)).save(
                        f"{output_path}/{rel}")
                    content = f"images/{rel}"
                else:
                    rect = fitz.Rect(x0 / RENDER_SCALE, y0 / RENDER_SCALE, x1 / RENDER_SCALE, y1 / RENDER_SCALE)
                    content = page.get_text("text", clip=rect)
                out.append(
                    {"page": pno, "class": r["c"], "x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1),
                     "conf": float(r["p"]), "content": content})
    return out

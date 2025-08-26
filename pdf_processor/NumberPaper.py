import re, statistics, io, contextlib
import shutil

import fitz


def is_numbered_pdf(pdf_path):
    RX = re.compile(r"^\d{1,4}[.)]?$")

    def get_words(p):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                return p.get_text("words")
            except:
                return []

    def side_score(words, side, W, side_band_frac=0.15, max_band_width_frac=0.12, min_hits=8, min_increase_frac=0.60):
        band = ([w for w in words if w[2] <= W * side_band_frac] if side == "left"
                else [w for w in words if w[0] >= W * (1 - side_band_frac)])
        ds = [w for w in band if RX.match(w[4])]
        if len(ds) < min_hits: return 0
        x0, x1 = min(w[0] for w in ds), max(w[2] for w in ds)
        if (x1 - x0) / max(W, 1e-6) > max_band_width_frac: return 0
        seq = sorted(ds, key=lambda w: (w[1], w[0]))
        inc = tot = 0;
        last = None
        for w in seq:
            s = re.sub(r"\D", "", w[4])
            if not s: continue
            n = int(s)
            if last is not None:
                tot += 1
                if n > last: inc += 1
            last = n
        return 1 if (tot and inc / tot >= min_increase_frac) else 0

    with fitz.open(pdf_path) as doc:
        k = min(3, len(doc))
        if k == 0: return False, None
        sides = []
        for i in range(k):
            p = doc.load_page(i)
            W = p.rect.width
            words = get_words(p)
            if not words:
                sides.append(None);
                continue
            sl = side_score(words, "left", W)
            sr = side_score(words, "right", W)
            if sl > 0 and sr == 0:
                sides.append("left")
            elif sr > 0 and sl == 0:
                sides.append("right")
            else:
                sides.append(None)
        if all(s is not None for s in sides) and len(set(sides)) == 1:
            return True, sides[0]
        return False, None


def _clean_margin(input_pdf_path, output_pdf_path, which="left"):
    doc = fitz.open(input_pdf_path)
    for page in doc:
        W, H = page.rect.width, page.rect.height
        words = page.get_text("words")
        if not words: continue
        body_heights = [(y1 - y0) for x0, y0, x1, y1, t, *_ in words if re.search(r"[A-Za-z]", t)]
        h_med = statistics.median(body_heights) if body_heights else None
        h_min = max(3.0, 0.5 * h_med) if h_med else 3.0
        h_max = min(0.12 * H, 1.7 * h_med) if h_med else 0.12 * H
        cands = []
        for x0, y0, x1, y1, t, *_ in words:
            s = re.sub(r"\D", "", t.strip())
            if not (s.isdigit() and 1 <= len(s) <= 4): continue
            w = x1 - x0;
            h = y1 - y0
            if h <= 0 or w <= 0: continue
            if not (h_min <= h <= h_max): continue
            cx = 0.5 * (x0 + x1)
            if which == "left":
                if cx > 0.30 * W: continue
            else:
                if cx < 0.70 * W: continue
            cands.append((x0, y0, x1, y1, cx))
        if len(cands) < 3: continue
        cxs = [c[4] for c in cands]
        med = statistics.median(cxs)
        mad = statistics.median([abs(x - med) for x in cxs]) or (0.002 * W)
        xtol = max(2.0, 4.0 * mad, 0.006 * W)
        xtol = min(xtol, 0.02 * W)
        strip = [c for c in cands if abs(c[4] - med) <= xtol]
        if len(strip) < 3: continue
        ys = [s[1] for s in strip] + [s[3] for s in strip]
        v_cov = (max(ys) - min(ys)) / max(H, 1e-6)
        if v_cov < 0.25: continue
        pad = 1.2
        for x0, y0, x1, y1, _ in strip:
            page.add_redact_annot(fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=(1, 1, 1))
        page.apply_redactions()
    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()


def clean_left_margin_line_numbers(input_pdf_path, output_pdf_path):
    _clean_margin(input_pdf_path, output_pdf_path, which="left")


def clean_right_margin_line_numbers(input_pdf_path, output_pdf_path):
    _clean_margin(input_pdf_path, output_pdf_path, which="right")


def clean_line_number(input_pdf_path, output_pdf_path):
    ok, side = is_numbered_pdf(input_pdf_path)
    if not ok:
        shutil.copy2(input_pdf_path, output_pdf_path)
        return

    if side == "left":
        clean_left_margin_line_numbers(input_pdf_path, output_pdf_path)
    else:
        clean_right_margin_line_numbers(input_pdf_path, output_pdf_path)

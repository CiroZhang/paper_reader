import re


def raise_key_word_to_header(jsonl_data):
    SUBHEADERS = [
        "abstract", "keywords", "introduction", "background", "literature review",
        "rationale", "objectives", "hypothesis", "research questions",
        "materials and methods", "materials", "methods", "study design",
        "participants", "subjects", "cohort description", "data collection",
        "experimental setup", "apparatus", "statistical analysis", "data analysis",
        "results", "statistical findings", "discussion", "interpretation of findings",
        "strengths", "limitations", "comparison with previous studies",
        "implications", "applications", "conclusion", "summary", "future work",
        "recommendations", "acknowledgements", "funding", "conflict of interest",
        "declarations", "references", "bibliography", "supplementary material"
    ]

    new_jsonl_data = []

    for json_data in jsonl_data:
        lines = json_data.get("content").strip()
        t = json_data.get("class")
        x0 = json_data.get("x0", 0.0)
        x1 = json_data.get("x1", 0.0)
        y0 = json_data.get("y0", 0.0)
        y1 = json_data.get("y1", 0.0)

        if t not in {"text", "caption"}:
            new_jsonl_data.append({
                "class": t, "content": lines, "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })
            continue

        processed_line = ""
        line_list = lines.split("\n")

        for line in line_list:
            if line in SUBHEADERS:
                new_jsonl_data.append({
                    "class": t, "content": processed_line,
                    "x0": x0, "x1": x1, "y0": y0, "y1": y1
                })

                new_jsonl_data.append({
                    "class": 'section-header',
                    "content": line,
                    "x0": x0, "x1": x1, "y0": y0, "y1": y1
                })

                processed_line = ""
            processed_line += line + "\n"

        new_jsonl_data.append({
            "class": t, "content": processed_line,
            "x0": x0, "x1": x1, "y0": y0, "y1": y1
        })

    return new_jsonl_data


def raise_numbered_labels_to_list(jsonl_data):
    new_jsonl_data = []

    for json_data in jsonl_data:
        lines = json_data.get("content").strip()
        t = json_data.get("class")
        x0 = json_data.get("x0", 0.0)
        x1 = json_data.get("x1", 0.0)
        y0 = json_data.get("y0", 0.0)
        y1 = json_data.get("y1", 0.0)

        if t not in {"text", "caption"}:
            new_jsonl_data.append({
                "class": t, "content": lines, "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })
            continue

        if re.match(r'^\s{0,2}(?:\[\d+\]|\d+\.)\s+\S', lines):

            new_jsonl_data.append({
                "class": "list-item", "content": lines,
                "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })

        else:
            new_jsonl_data.append({
                "class": "text", "content": lines,
                "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })

    return new_jsonl_data


def merge_close_text_boxes(items):
    def _first_alpha_case(s: str):
        for ch in s.strip():
            if ch.isalpha():
                return 'upper' if ch.isupper() else 'lower'
        return None

    def _super_close(a, b, *, max_vgap_frac=0.35, tol_left_frac=0.08, tol_width_frac=0.15):
        ax0, ay0, ax1, ay1 = a["x0"], a["y0"], a["x1"], a["y1"]
        bx0, by0, bx1, by1 = b["x0"], b["y0"], b["x1"], b["y1"]

        ah = max(1.0, ay1 - ay0)
        aw = max(1.0, ax1 - ax0)
        bw = max(1.0, bx1 - bx0)

        vgap = by0 - ay1
        if not (0 <= vgap <= max_vgap_frac * ah):
            return False

        if abs(bx0 - ax0) > tol_left_frac * aw:
            return False

        wr = bw / aw
        if not (1 - tol_width_frac <= wr <= 1 + tol_width_frac):
            return False

        return True

    if not items:
        return items

    merged = []
    i = 0
    n = len(items)

    while i < n:
        curr = items[i]
        if curr.get("class") != "text":
            merged.append(curr)
            i += 1
            continue

        case = _first_alpha_case(curr.get("content", ""))
        if case != 'upper':
            merged.append(curr)
            i += 1
            continue

        run = dict(curr)
        j = i + 1
        while j < n:
            nxt = items[j]
            if nxt.get("class") != "text":
                break

            nxt_case = _first_alpha_case(nxt.get("content", ""))
            if nxt_case != 'lower':
                break

            if not _super_close(run, nxt):
                break

            sep = " "
            run["content"] = (run["content"].rstrip() + sep + nxt.get("content", "").strip()).strip()
            run["x0"] = min(run["x0"], nxt["x0"])
            run["y0"] = min(run["y0"], nxt["y0"])
            run["x1"] = max(run["x1"], nxt["x1"])
            run["y1"] = max(run["y1"], nxt["y1"])

            j += 1

        merged.append(run)
        i = j

    return merged


def noise_filter(jsonl_data):
    def normalize_spaces(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").replace("\t", " ")).strip()

    def space_density(s: str) -> float:
        if not s:
            return 0.0
        total = len(s)
        spaces = sum(1 for c in s if c == " ")
        return spaces / total if total else 0.0

    new_jsonl_data = []
    for json_data in jsonl_data:
        lines = (json_data.get("content") or "").strip()
        t = (json_data.get("class") or "").lower()

        x0 = json_data.get("x0", 0.0)
        x1 = json_data.get("x1", 0.0)
        y0 = json_data.get("y0", 0.0)
        y1 = json_data.get("y1", 0.0)

        if t in {"picture", "table", "formula"}:
            new_jsonl_data.append({
                "class": t, "content": lines, "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })
            continue

        if t in {"page-header", "page-footer", "footnote"}:
            continue

        if t in {"title", "section-header"}:
            lines = normalize_spaces(lines)
            new_jsonl_data.append({
                "class": t, "content": lines, "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })
            continue

        lines = lines.replace("-\n", "")
        line_list = lines.split("\n")
        processed_line = " "

        for line in line_list:
            line = normalize_spaces(line)

            if len(line) <= 2:
                continue
            if space_density(line) > 0.5:
                continue
            if len(line.replace(" ", "")) < 3:
                continue

            processed_line += line + " "

        content = processed_line.strip()

        if len(content) < 2:
            continue

        new_jsonl_data.append({
            "class": t, "content": content,
            "x0": x0, "x1": x1, "y0": y0, "y1": y1
        })
    return new_jsonl_data


def process_yolo_output(jsonl_data):
    jsonl_data = raise_key_word_to_header(jsonl_data)
    jsonl_data = noise_filter(jsonl_data)
    jsonl_data = merge_close_text_boxes(jsonl_data)
    jsonl_data = raise_numbered_labels_to_list(jsonl_data)
    return jsonl_data

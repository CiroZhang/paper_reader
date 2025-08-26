import re
import statistics


def list_grouper(jsonl_data):
    def commit_group(group, out):
        if not group:
            return
        if len(group) == 1:
            solo = (group[0] or "").strip()
            wc = len(solo.split())
            if wc <= 2:
                out.append({"class": "section-header", "content": solo})
            else:
                out.append({"class": "text", "content": solo})
        else:
            out.append({"class": "list-item", "content": group})

    grouped_data = []
    temp_group = []

    for json_data in jsonl_data:
        t = json_data.get("class")
        lines = json_data.get("content", "")

        if t == "list-item":
            temp_group.append(lines)
        else:
            commit_group(temp_group, grouped_data)
            temp_group = []
            grouped_data.append(json_data)

    commit_group(temp_group, grouped_data)

    return grouped_data


def abstract_label_filter(jsonl_data):
    new_jsonl_data = []
    start_idx = 0

    for i, json_data in enumerate(jsonl_data):
        line = json_data["content"].strip()
        t = json_data["class"].lower()

        if 'abstract' in line.lower() and t in {"title", "section-header"}:
            start_idx = i
            new_jsonl_data.append({
                "content": 'Abstract',
                "class": "section-header"
            })
            break

        if 'introduction' in line.lower() and t in {"title", "section-header"}:
            start_idx = i
            new_jsonl_data.append({
                "content": 'Introduction',
                "class": "section-header"
            })
            break

    if start_idx == 0:
        return jsonl_data, []

    removed = jsonl_data[:start_idx]

    new_jsonl_data += jsonl_data[start_idx + 1:]
    return new_jsonl_data, removed


def reference_label_filter(jsonl_data):
    removed = []
    skip_mode = False
    rew_jsonl_data = []

    for i, json_data in enumerate(jsonl_data):
        line = json_data["content"].strip()
        t = json_data["class"].lower()

        if not skip_mode and 'references' in line.lower() and t in {"title", "section-header"}:
            skip_mode = True
            continue

        if skip_mode:
            if t == "list-item":
                removed.append(json_data)
                continue

            else:
                skip_mode = False

        rew_jsonl_data.append(json_data)

    return rew_jsonl_data, removed


def comma_percent(text):
    if not text:
        return 0

    c = text.count(",")
    return c / len(text)


def ref_score(t):
    RX_YEAR = re.compile(r"\b(19|20)\d{2}\b")
    RX_PAGES = re.compile(r"\b(?:pp\.?\s*)?\d{1,5}\s*[-–]\s*\d{1,5}\b", re.I)
    RX_VOL_ISSUE = re.compile(
        r"\b(?:vol\.?\s*\d+|no\.?\s*\d+|volume\s*\d+|\d+\s*\(\d+\)|\d{1,4}\s*,\s*\d{1,5}(?:[-–]\d{1,5})?)\b", re.I)
    RX_DOI_ARXIV = re.compile(r"\b(doi:\S+|https?://doi\.org/\S+|arXiv:\S+)\b", re.I)
    RX_PROCEEDINGS = re.compile(
        r"\b(Proc\.|Proceedings|ICCV|CVPR|ECCV|MICCAI|NeurIPS|ICML|AAAI|IJCAI|TIP|TMI|PAMI)\b")
    RX_BRACKET_IDX = re.compile(r"^\s*\[\d+\]")
    RX_NUM_IDX = re.compile(r"^\s*\d+\.\s+")
    RX_AUTHORS_ABS = re.compile(r"\b(?:[A-Z]\.\s*){1,3}[A-Z][a-zA-Z\-']+\b")
    RX_AUTHORS_SAB = re.compile(r"\b[A-Z][a-zA-Z\-']+,\s*(?:[A-Z]\.\s*){1,3}\b")
    RX_FIGURE = re.compile(r"^\s*(Fig\.?|Figure)\b", re.I)
    RX_SECTION = re.compile(r"^\s*(Section|Sec\.?)\b", re.I)
    RX_SENTENCE_END = re.compile(r"[.!?]\s+[A-Z]")
    RX_HTTP = re.compile(r"https?://", re.I)
    SPLIT_NUMBERED = re.compile(r"\s(?=\d+\.\s+[A-Z])")

    t = " ".join(t.strip().split())
    s = 0.0
    has_year = bool(RX_YEAR.search(t))
    has_pages = bool(RX_PAGES.search(t))
    has_vi = bool(RX_VOL_ISSUE.search(t))
    has_doi = bool(RX_DOI_ARXIV.search(t))
    has_proc = bool(RX_PROCEEDINGS.search(t))
    has_idx = bool(RX_BRACKET_IDX.search(t) or RX_NUM_IDX.search(t))
    has_auth = bool(RX_AUTHORS_ABS.search(t) or RX_AUTHORS_SAB.search(t))
    has_http = bool(RX_HTTP.search(t))
    s += 1.2 if has_idx else 0.0
    s += 1.0 if has_year else 0.0
    s += 1.0 if has_pages else 0.0
    s += 0.8 if has_vi else 0.0
    s += 1.2 if has_doi else 0.0
    s += 1.0 if has_proc else 0.0
    s += 1.0 if has_auth else 0.0
    s += 1.0 if has_http else 0.0
    commas = t.count(",")
    if commas >= 2:
        s += min(0.8, 0.2 * (commas - 1))
    strong = sum([has_idx, has_year, has_pages, has_vi, has_doi, has_auth]) >= 2
    if RX_FIGURE.search(t):
        s -= 1.5
    if RX_SECTION.search(t):
        s -= 0.8
    if RX_SENTENCE_END.search(t) and not strong:
        s -= 1.2
    n = len(t)
    if n < 20:
        s -= 0.8
    elif n > 450 and not strong:
        s -= 0.8
    return s


def group_ref_score(group_text):
    scores = [ref_score(text) for text in group_text]
    return statistics.median(scores)


def itemlist_reference_filter(jsonl_data):
    new_jsonl_data = []
    removed = []
    grouped = list_grouper(jsonl_data)

    for i, json_data in enumerate(grouped):
        lines = json_data.get("content")
        t = json_data.get("class")

        if t != "list-item":
            new_jsonl_data.append(json_data)



        elif group_ref_score(lines) >= 0.5:

            removed += [{"class": t, "content": line} for line in lines]

        else:
            new_jsonl_data += [{"class": t, "content": line} for line in lines]

    return new_jsonl_data, removed


def keyword_reference_filter(jsonl_data):
    new_jsonl_data = []
    removed = []

    for json_data in jsonl_data:
        line = json_data["content"].strip()
        t = json_data["class"].lower()

        if t in {"picture", "table", "formula"}:
            new_jsonl_data.append(json_data)
            continue

        if t == "list-item":
            if line.find(" ") == -1 and line.replace(".", "").replace(",", "").replace(":", "").isalpha():
                new_jsonl_data.append(json_data)
                continue

            if "[" in line[:10] or "]" in line[:10]:
                removed.append(json_data)
                continue

            if "( )" in line[:15]:
                removed.append(json_data)
                continue

            if "() " in line[:15]:
                removed.append(json_data)
                continue

            if ref_score(line) > 1:
                removed.append(json_data)
                continue

            if "." in line and comma_percent(line[4:].split(".")[0]) > 0.05:
                removed.append(json_data)
                continue

        if " [internet]" in line:
            removed.append(json_data)
            continue

        if "[cited" in line:
            removed.append(json_data)
            continue

        if ("university of" in line[:30].lower() or
            "college of" in line[:30].lower() or
            "department of" in line[:30].lower()) and len(line) < 300:
            removed.append(json_data)
            continue

        if ref_score(line) > 2:
            removed.append(json_data)
            continue

    return jsonl_data, removed


def reference_filter(jsonl_data):
    removed = []

    jsonl_data, remove = abstract_label_filter(jsonl_data)
    removed += remove

    jsonl_data, remove = reference_label_filter(jsonl_data)
    removed += remove

    jsonl_data, remove = itemlist_reference_filter(jsonl_data)
    removed += remove

    jsonl_data, remove = keyword_reference_filter(jsonl_data)
    removed += remove

    return jsonl_data, removed

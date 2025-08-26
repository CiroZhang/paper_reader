import os, re


def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ").strip()
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.replace("-\n", "")
    s = s.replace("\n", "\n")
    return s


def convert_jsonl_to_md(jsonl_data):
    md_text = ""

    for json_data in jsonl_data:
        # page = int(json_data["page"])
        content = json_data["content"].strip()
        t = json_data["class"].lower()

        if t in {"picture", "table", "formula"}:
            path = str(content)
            alt = {"picture": "Figure", "table": "Table", "formula": "Formula"}.get(t, "Image")
            name = os.path.basename(path)
            md_text += f"![{alt} - {name}]({path})\n\n"

        elif t in {"title", "section-header"}:
            txt = _clean_text(str(content))
            md_text += f"\n\n{txt}\n\n"

        elif t == "text":
            txt = _clean_text(str(content))
            md_text += f"{txt}\n"

        elif t == "caption":
            txt = _clean_text(str(content))
            md_text += f"{txt}\n\n"

        elif t == "list-item":
            txt = _clean_text(str(content))
            md_text += f"- {txt}\n"

        elif t in {"page-header", "page-footer", "footnote"}:
            continue

    return md_text

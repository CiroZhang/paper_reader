import re
from typing import List, Tuple, Dict, Any


def remove_cc_license_prefix(text):
    pattern = re.compile(
        r"""
        \bCC              # CC
        (?:[\s\-]*BY)?    # optional BY
        (?:[\s\-]*NC)?    # optional NC
        (?:[\s\-]*ND)?    # optional ND
        \s*               # optional space
        4[.\s]?0          # 4.0
        \s*International\s+license\s+It\s+is\s+made\s+available\s+under\s+a
        """,
        re.VERBOSE | re.IGNORECASE
    )
    removed: List[str] = []

    def _sub(m: re.Match) -> str:
        removed.append(m.group(0))
        return ""

    cleaned = pattern.sub(_sub, text)
    return cleaned, removed


def delete_license(text, accept_rxiv):
    removed: List[str] = []
    low = text.lower()

    if ("international license" in low and len(text) < 150) or \
            ("all rights reserved" in low and len(text) < 150):
        return "", [text]

    pattern = re.compile(
        r"(?:cc|all\s+rights|is the author/funder).*?medRxiv preprint",
        flags=re.IGNORECASE | re.DOTALL
    )

    to_delete: List[Tuple[int, int]] = []
    for m in pattern.finditer(text):
        span = m.group(0)
        lowspan = span.lower()
        has_license = "license" in lowspan
        has_rxiv = ("rxiv" in lowspan) if accept_rxiv else ("medrxiv" in lowspan)
        if has_license and has_rxiv:
            to_delete.append((m.start(), m.end()))

    if to_delete:
        parts, last = [], 0
        for start, end in to_delete:
            parts.append(text[last:start])
            removed.append(text[start:end])
            last = end
        parts.append(text[last:])
        text = "".join(parts)

    text, removed_prefixes = remove_cc_license_prefix(text)
    removed.extend(removed_prefixes)
    
    phrase = "who has granted medRxiv a license to display the preprint in perpetuity"
    if phrase in text:
        text = text.replace(phrase, "")
        removed.append(phrase)

    return text.strip(), removed


def license_filter(jsonl_data, accept_rxiv = True):

    new_jsonl_data = []
    removed_items = []

    for json_data in jsonl_data:
        lines = json_data.get("content", "")
        t = json_data.get("class")
        x0 = json_data.get("x0", 0.0)
        x1 = json_data.get("x1", 0.0)
        y0 = json_data.get("y0", 0.0)
        y1 = json_data.get("y1", 0.0)

        cleaned, removed_parts = delete_license(lines, accept_rxiv=accept_rxiv)

        new_jsonl_data.append({
            "class": t,
            "content": cleaned,
            "x0": x0, "x1": x1, "y0": y0, "y1": y1
        })

        if removed_parts:
            removed_items.append({
                "class": t,
                "content": "\n".join(part.strip() for part in removed_parts if part.strip()),
                "x0": x0, "x1": x1, "y0": y0, "y1": y1
            })

    return new_jsonl_data, removed_items

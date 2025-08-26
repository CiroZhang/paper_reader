import torch
from transformers import pipeline

ner_pipeline = pipeline("token-classification", model="dslim/bert-base-NER", aggregation_strategy="simple")


def name_filter(jsonl_data):
    new_jsonl_data = []
    removed = []

    for json_data in jsonl_data:
        line = json_data["content"].strip()
        t = json_data["class"].lower()

        beg = line.strip()[:60]
        pers = [p['word'] for p in ner_pipeline(beg) if p["entity_group"] == "PER"]

        if len(pers) >= 3:
            removed.append(json_data)
            continue

        new_jsonl_data.append(json_data)

    return new_jsonl_data, removed

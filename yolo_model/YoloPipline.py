from .YoloHelper import process_yolo_output
from .YoloModel import get_yolo_output


def yolo_pipeline(pdf_name, pdf_path, image_output_path):
    jsonl_data = get_yolo_output(pdf_name, pdf_path, image_output_path)
    jsonl_data = process_yolo_output(jsonl_data)
    return jsonl_data

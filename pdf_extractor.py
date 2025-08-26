import json, os, shutil
from pathlib import Path
from tqdm import tqdm

from markdown_coverter import convert_jsonl_to_md
from yolo_model.YoloPipline import yolo_pipeline
from pdf_processor.PdfTrimmer import trim_sides
from pdf_processor.NumberPaper import clean_line_number
from text_filters.LicenseFilter import license_filter
from text_filters.ReferenceFilter import reference_filter


def read_jsonl(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def export_pdfs_to_mds(input_folder, output_folder, save_raw_json=True, save_removed=False):
    shutil.rmtree(output_folder, ignore_errors=True)
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    temp_dir = Path("__cut_tmp__")
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".pdf")]
    for pdf_file in tqdm(pdf_files, desc="Trimming PDFs", unit="file"):
        src_pdf = Path(input_folder) / pdf_file
        tmp_pdf = temp_dir / pdf_file
        pre_pdf = temp_dir / f"{src_pdf.stem}__pre.pdf"

        try:
            trim_sides(str(src_pdf), str(pre_pdf), top=0.05)
            clean_line_number(str(pre_pdf), str(tmp_pdf))
        except Exception:
            continue

    image_folder = f'{output_folder}/outputs/images'
    md_folder = f'{output_folder}/outputs'
    jsonl_folder = f'{output_folder}/raw_outputs'
    removed_folder = f'{output_folder}/removed'

    Path(image_folder).mkdir(parents=True, exist_ok=True)
    Path(md_folder).mkdir(parents=True, exist_ok=True)
    Path(jsonl_folder).mkdir(parents=True, exist_ok=True)
    Path(removed_folder).mkdir(parents=True, exist_ok=True)

    skipped = []

    for pdf_file in tqdm(pdf_files, desc="run YOLO on prepared PDFs", unit="file"):
        pdf_name = pdf_file[:-4]
        yolo_pdf = temp_dir / pdf_file

        res_dir = Path(image_folder) / pdf_name
        shutil.rmtree(res_dir, ignore_errors=True)
        res_dir.mkdir(parents=True, exist_ok=True)

        try:

            jsonl_data = yolo_pipeline(pdf_name, str(yolo_pdf), image_folder)
            jsonl_data, removed_licenses = license_filter(jsonl_data)
            jsonl_data, removed_reference = reference_filter(jsonl_data)

            md_data = convert_jsonl_to_md(jsonl_data)
            with open(Path(md_folder) / f"{pdf_name}.md", "w", encoding="utf-8", newline="\n") as f:
                f.write(md_data.rstrip() + "\n")

            if save_raw_json:
                jsonl_path = Path(jsonl_folder) / f"{pdf_name}.jsonl"
                with open(jsonl_path, "w", encoding="utf-8") as f:
                    for item in jsonl_data:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")

            if save_removed:
                md_removed_licenses = convert_jsonl_to_md(removed_licenses)
                with open(Path(removed_folder) / f"{pdf_name}_removed_licenses.md", "w", encoding="utf-8",
                          newline="\n") as f:
                    f.write(md_removed_licenses.rstrip() + "\n")

                md_removed_reference = convert_jsonl_to_md(removed_reference)
                with open(Path(removed_folder) / f"{pdf_name}_removed_reference.md", "w", encoding="utf-8",
                          newline="\n") as f:
                    f.write(md_removed_reference.rstrip() + "\n")
        except:
            skipped.append(pdf_file)


    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f'failed to process {len(skipped)} pdfs')
    return skipped


# PDF to Markdown Converter (with YOLO-based Layout Detection)

This project provides a pipeline to **convert academic/research PDFs into cleaned Markdown files**, with support for:
- **Trimming margins** and removing line numbers.
- **YOLO-based region detection** (text, tables, figures, formulas).
- **Post-processing filters** for noise, licenses, and references.
- **Markdown export** with embedded images for figures/tables.
- **Optional raw JSONL outputs** for downstream processing.

---

## 📂 Project Structure

```
.
├── main.py
├── pdf_extractor.py
├── markdown_coverter.py
├── yolo_model/
│   ├── YoloModel.py
│   ├── YoloHelper.py
│   ├── YoloPipline.py
│   └── doclaynet.pt   # YOLO model weights (DocLayNet)
├── pdf_processor/
│   ├── NumberPaper.py
│   └── PdfTrimmer.py
├── text_filters/
│   ├── LicenseFilter.py
│   └── ReferenceFilter.py
```

---

## ⚙️ Modules Overview

### **1. PDF Preprocessing**
- **`PdfTrimmer.py`** – trims page margins (top, bottom, left, right) while avoiding rotated pages.
- **`NumberPaper.py`** – detects and removes line numbers from PDF margins using heuristics.

### **2. YOLO-based Layout Extraction**
- **`YoloModel.py`** – runs YOLO (DocLayNet weights) on PDF pages to detect text, figures, tables, and formulas.
- **`YoloHelper.py`** – processes YOLO outputs: merges bounding boxes, removes noise, raises headers, and restructures text.
- **`YoloPipline.py`** – orchestrates detection + post-processing into JSONL outputs.

### **3. Text Processing & Export**
- **`markdown_coverter.py`** – converts processed JSONL into Markdown format, embedding images when available.
- **`LicenseFilter.py`** – removes boilerplate license/rights text.
- **`ReferenceFilter.py`** – removes references/bibliographies and cleans extraneous text.

### **4. Pipeline Entry Points**
- **`pdf_extractor.py`** – core pipeline that:
  1. Trims PDFs and removes line numbers.
  2. Runs YOLO layout extraction.
  3. Applies license/reference filters.
  4. Saves `.md`, `.jsonl`, and removed sections.
- **`main.py`** – example script to run extraction on a folder of PDFs.

---

## 🚀 Usage

### 1. Install Dependencies
```
pip install -r requirements.txt
```
Dependencies include:
- `PyMuPDF` (`fitz`)
- `PyPDF2`
- `ultralytics` (YOLOv8)
- `Pillow`
- `tqdm`

### 2. Prepare Model Weights
Download [DocLayNet YOLO weights](https://github.com/DocLayNet) and place as:
```
yolo_model/doclaynet.pt
```

### 3. Run the Pipeline
```
python main.py
```

By default, `main.py` calls:
```python
from pdf_extractor import export_pdfs_to_mds

failed = export_pdfs_to_mds(
    input_folder="paper/前列腺癌",   # input folder containing PDFs
    output_folder="前列腺癌",        # output folder for results
    save_raw_json=True,             # save raw JSONL
    save_removed=True               # save removed sections
)
```

### 4. Outputs
After running, you’ll get:
```
output_folder/
│── outputs/
│   ├── <paper_name>.md          # Final Markdown
│── outputs/images/              # Extracted figures/tables
│── raw_outputs/                 # JSONL structured outputs
│── removed/                     # Removed license/reference sections
```

---

## 🧩 Example Workflow
1. Place your PDFs into `paper/<topic>/`.
2. Run `python main.py`.
3. Check `outputs/` for Markdown files.
4. Open `.md` files in any Markdown editor to view cleaned text + figures.

---

## 📜 License
This project is provided for **research and educational purposes**.  
Make sure you comply with dataset (DocLayNet) and paper license terms when processing PDFs.

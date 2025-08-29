from PyPDF2 import PdfReader, PdfWriter

def trim_sides(input_path, output_path, top=0.0, bottom=0.0, left=0.0, right=0.0):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    stop_cutting = False

    for page in reader.pages:
        if stop_cutting:
            writer.add_page(page)
            continue

        try:
            rot = int(getattr(page, "rotation", 0)) % 360
        except Exception:
            rot = 0

        if rot != 0:  # non-standard page → stop trimming from here on
            stop_cutting = True
            writer.add_page(page)
            continue

        mb = page.mediabox
        llx, lly = float(mb.lower_left[0]), float(mb.lower_left[1])
        urx, ury = float(mb.upper_right[0]), float(mb.upper_right[1])

        width = urx - llx
        height = ury - lly

        # Apply fractional cuts
        new_llx = llx + left * width
        new_lly = lly + bottom * height
        new_urx = urx - right * width
        new_ury = ury - top * height

        # Guard against invalid crop boxes
        eps = 1e-3
        if new_urx - new_llx < eps:
            midx = (llx + urx) / 2
            new_llx, new_urx = midx - eps / 2, midx + eps / 2
        if new_ury - new_lly < eps:
            midy = (lly + ury) / 2
            new_lly, new_ury = midy - eps / 2, midy + eps / 2

        page.cropbox.lower_left = (new_llx, new_lly)
        page.cropbox.upper_right = (new_urx, new_ury)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

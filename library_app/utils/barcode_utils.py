"""
Barcode generation utility — Code128 barcodes + PDF label export
"""

import io
import os
import tempfile
from pathlib import Path

try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def generate_barcode_image(code: str, save_path: str = None) -> bytes:
    """Generate a clean Code128 barcode image (bars only, no text). Returns PNG bytes."""
    if not BARCODE_AVAILABLE or not PIL_AVAILABLE:
        raise RuntimeError("python-barcode and Pillow are required")

    code128 = barcode.get("code128", code, writer=ImageWriter())
    buf = io.BytesIO()
    # High resolution, no built-in text (we draw crisp vector text in reportlab)
    options = {
        "write_text": False,
        "module_height": 10.0,
        "module_width": 0.4,
        "quiet_zone": 2.0,
    }
    code128.write(buf, options=options)
    buf.seek(0)
    img_bytes = buf.read()

    if save_path:
        with open(save_path, "wb") as f:
            f.write(img_bytes)

    return img_bytes


def generate_qr_image(text: str, save_path: str = None) -> bytes:
    """Generate a high-contrast, phone-screen scannable 2D QR code image (PNG bytes)."""
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    if save_path:
        with open(save_path, "wb") as f:
            f.write(img_bytes)
    return img_bytes



def generate_barcode_pdf(items: list, output_path: str, label_type: str = "book"):
    """
    Generate a perfectly aligned printable PDF of barcode labels.
    Uses standard A4 sticker sheet layout: 3 columns x 8 rows = 24 labels per page.
    Fits all standard 63.5mm x 33.9mm / 64mm x 33.8mm label sheets.
    """
    if not REPORTLAB_AVAILABLE or not BARCODE_AVAILABLE or not PIL_AVAILABLE:
        raise RuntimeError("reportlab, python-barcode, and Pillow are required")

    page_w, page_h = A4  # 210mm x 297mm

    # 3 columns x 8 rows = 24 labels per page
    cols = 3
    rows = 8
    labels_per_page = cols * rows

    label_w = 63.5 * mm
    label_h = 32.5 * mm

    gap_x = 2.5 * mm
    gap_y = 2.0 * mm

    # Exact centering on A4
    total_grid_w = (cols * label_w) + ((cols - 1) * gap_x)  # ~195.5mm
    total_grid_h = (rows * label_h) + ((rows - 1) * gap_y)  # ~274mm

    margin_x = (page_w - total_grid_w) / 2.0  # ~7.25mm
    margin_y_bottom = (page_h - total_grid_h) / 2.0  # ~11.5mm

    c = canvas.Canvas(output_path, pagesize=A4)

    total_items = len(items)
    page_count = (total_items + labels_per_page - 1) // labels_per_page
    item_idx = 0
    curr_page = 1

    while item_idx < total_items:
        # Running header at very top margin
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.HexColor("#4A5568"))
        header_title = "SRM Institute of Science and Technology — Department of Electrical & Electronics Engineering"
        c.drawString(margin_x, page_h - 7 * mm, header_title)

        page_str = f"Page {curr_page} of {page_count}"
        c.drawRightString(page_w - margin_x, page_h - 7 * mm, page_str)

        for r in range(rows):
            for col in range(cols):
                if item_idx >= total_items:
                    break
                item = items[item_idx]
                item_idx += 1

                x = margin_x + col * (label_w + gap_x)
                # Count from top row (r=0) downwards
                y = page_h - margin_y_bottom - ((r + 1) * label_h) - (r * gap_y)

                # Label border (rounded light gray box)
                c.setStrokeColor(colors.HexColor("#CBD5E1"))
                c.setLineWidth(0.6)
                c.setFillColor(colors.HexColor("#FFFFFF"))
                c.roundRect(x, y, label_w, label_h, 1.8 * mm, stroke=1, fill=1)

                # Top micro-header inside label
                c.setFont("Helvetica-Bold", 5.5)
                c.setFillColor(colors.HexColor("#1E40AF"))
                header_text = "SRM EEE LIBRARY" if label_type == "book" else "SRM EEE DEPARTMENT"
                c.drawString(x + 2.5 * mm, y + label_h - 4.0 * mm, header_text)

                # Barcode Image
                barcode_str = str(item.get("barcode", "")).strip()
                try:
                    img_bytes = generate_barcode_image(barcode_str)
                    img = Image.open(io.BytesIO(img_bytes))
                    bbox = img.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                    img_buf = io.BytesIO()
                    img.save(img_buf, format="PNG")
                    img_buf.seek(0)
                    img_reader = ImageReader(img_buf)

                    # Draw barcode cleanly centered
                    bc_w = label_w - 6 * mm
                    bc_h = 11.5 * mm
                    bc_x = x + 3 * mm
                    bc_y = y + label_h - 16.5 * mm

                    c.drawImage(img_reader, bc_x, bc_y, width=bc_w, height=bc_h, preserveAspectRatio=False)
                except Exception:
                    pass

                # Barcode Text (sharp, centered below the bars)
                c.setFont("Courier-Bold", 7.5)
                c.setFillColor(colors.HexColor("#0F172A"))
                c.drawCentredString(x + (label_w / 2.0), y + label_h - 20.0 * mm, barcode_str)

                # Item Main Title / Name
                c.setFont("Helvetica-Bold", 6.8)
                c.setFillColor(colors.HexColor("#111827"))
                name_text = str(item.get("name", "")).strip()
                if len(name_text) > 34:
                    name_text = name_text[:32] + "…"
                c.drawString(x + 2.5 * mm, y + 6.2 * mm, name_text)

                # Item Extra Info (Class / Author / Register No)
                c.setFont("Helvetica", 5.8)
                c.setFillColor(colors.HexColor("#475569"))
                extra_text = str(item.get("extra", "")).strip()
                if len(extra_text) > 42:
                    extra_text = extra_text[:40] + "…"
                c.drawString(x + 2.5 * mm, y + 2.5 * mm, extra_text)

        c.showPage()
        curr_page += 1

    c.save()
    return output_path

"""
SRM EEE Department Library — A4 Promotional Poster Generator
Generates high-resolution, print-ready vector PDF posters matching the website theme:
- Deep Forest Green (#1C3022) & Rich Sage (#48634E)
- Mentions the website URL prominently
- Mentions the Digital Library Barcode emailed to students
"""

import io
import os
import qrcode
from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def generate_qr_image(url: str) -> Image.Image:
    """Generate high-contrast QR code as PIL image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    # Deep forest green QR code dots
    return qr.make_image(fill_color="#1C3022", back_color="white").convert("RGB")


def build_poster_pdf(target_url: str = "https://srm-eee-library.onrender.com", output_path: str = None) -> bytes:
    """
    Builds a vector-crisp A4 poster PDF matching the official SRM EEE Library website design.
    Returns bytes or writes to output_path.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer if not output_path else output_path, pagesize=A4)
    width, height = A4  # 595.27 x 841.89 points

    # Website Theme Colors
    FOREST_GREEN = colors.HexColor("#1C3022")
    FOREST_DARK = colors.HexColor("#122116")
    SAGE_ACCENT = colors.HexColor("#48634E")
    SAGE_LIGHT = colors.HexColor("#EBF2E9")
    EMERALD = colors.HexColor("#166534")
    MINT_GREEN = colors.HexColor("#86EFAC")
    TEXT_DARK = colors.HexColor("#17241A")
    TEXT_MUTED = colors.HexColor("#57685A")
    BG_CREAM = colors.HexColor("#F4F6F1")
    BORDER_LIGHT = colors.HexColor("#DCE5D8")

    # Clean URL string for display
    display_url = target_url.replace("https://", "").replace("http://", "").rstrip("/")

    # 1. Page Background (Crisp White)
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # 2. Header Area
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "webapp", "static", "images", "srm_logo.png")
    header_y = height - 52

    if os.path.exists(logo_path):
        c.drawImage(logo_path, 34, header_y - 10, width=44, height=44, mask="auto")

    # SRM University Text
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(FOREST_GREEN)
    c.drawString(86, header_y + 16, "SRM")

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(TEXT_DARK)
    c.drawString(130, header_y + 19, "INSTITUTE OF SCIENCE & TECHNOLOGY")
    c.setFont("Helvetica", 5.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(130, header_y + 11, "(Deemed to be University u/s 3 of UGC Act, 1956)")

    # Vertical Divider Line
    c.setStrokeColor(BORDER_LIGHT)
    c.setLineWidth(1)
    c.line(285, header_y - 8, 285, header_y + 26)

    # Department Library Title
    c.setFont("Helvetica-Bold", 13.5)
    c.setFillColor(FOREST_GREEN)
    c.drawString(298, header_y + 14, "EEE DEPARTMENT")
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(SAGE_ACCENT)
    c.drawString(298, header_y + 1, "DEPARTMENT LIBRARY")

    # 3. Hero Dark Forest Green Banner
    hero_top = height - 72
    hero_height = 120
    hero_y = hero_top - hero_height

    c.setFillColor(FOREST_GREEN)
    c.rect(26, hero_y, width - 52, hero_height, fill=1, stroke=0)

    # Subtle inner decorative pattern
    c.setStrokeColor(colors.HexColor("#2A4433"))
    c.setLineWidth(0.7)
    for bx in range(36, int(width - 50), 32):
        c.rect(bx, hero_y + 6, 24, 40, fill=0, stroke=1)
        c.line(bx + 4, hero_y + 10, bx + 20, hero_y + 10)

    # Top Pill "OFFICIAL DEPARTMENT PORTAL"
    c.setFillColor(colors.HexColor("#27422F"))
    c.roundRect((width / 2.0) - 95, hero_y + 94, 190, 16, 8, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(MINT_GREEN)
    c.drawCentredString(width / 2.0, hero_y + 98, "OFFICIAL DEPARTMENT PORTAL")

    # Main Headline
    c.setFont("Times-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2.0, hero_y + 70, "ACCESS OUR DIGITAL LIBRARY —")

    # Sub Headline
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(MINT_GREEN)
    c.drawCentredString(width / 2.0, hero_y + 47, "SCAN & GET STARTED")

    # Website URL Badge
    url_pill_w = min(260, len(display_url) * 8.5 + 40)
    c.setFillColor(colors.white)
    c.roundRect((width - url_pill_w) / 2.0, hero_y + 18, url_pill_w, 20, 10, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(FOREST_GREEN)
    c.drawCentredString(width / 2.0, hero_y + 24, f"🌐  {display_url}")

    # 4. Center QR Code Card (Overlapping Hero Banner)
    qr_w = 166
    qr_h = 166
    qr_card_x = (width - qr_w) / 2.0
    qr_card_y = hero_y - (qr_h * 0.44)

    # Shadow & Card Border
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.roundRect(qr_card_x + 3, qr_card_y - 3, qr_w, qr_h, 14, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setStrokeColor(BORDER_LIGHT)
    c.setLineWidth(1.5)
    c.roundRect(qr_card_x, qr_card_y, qr_w, qr_h, 14, fill=1, stroke=1)

    # Generate QR Code image and draw
    qr_pil = generate_qr_image(target_url)
    temp_qr_path = os.path.join(os.path.dirname(__file__), "_temp_qr_poster.png")
    qr_pil.save(temp_qr_path)
    c.drawImage(temp_qr_path, qr_card_x + 20, qr_card_y + 30, width=126, height=126)
    try:
        os.remove(temp_qr_path)
    except Exception:
        pass

    # QR Scan Brackets in Forest Green
    c.setStrokeColor(FOREST_GREEN)
    c.setLineWidth(2.5)
    # Top-Left
    c.line(qr_card_x + 12, qr_card_y + 152, qr_card_x + 24, qr_card_y + 152)
    c.line(qr_card_x + 12, qr_card_y + 152, qr_card_x + 12, qr_card_y + 140)
    # Top-Right
    c.line(qr_card_x + qr_w - 12, qr_card_y + 152, qr_card_x + qr_w - 24, qr_card_y + 152)
    c.line(qr_card_x + qr_w - 12, qr_card_y + 152, qr_card_x + qr_w - 12, qr_card_y + 140)
    # Bottom-Left
    c.line(qr_card_x + 12, qr_card_y + 30, qr_card_x + 24, qr_card_y + 30)
    c.line(qr_card_x + 12, qr_card_y + 30, qr_card_x + 12, qr_card_y + 42)
    # Bottom-Right
    c.line(qr_card_x + qr_w - 12, qr_card_y + 30, qr_card_x + qr_w - 24, qr_card_y + 30)
    c.line(qr_card_x + qr_w - 12, qr_card_y + 30, qr_card_x + qr_w - 12, qr_card_y + 42)

    # Caption
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(FOREST_GREEN)
    c.drawCentredString(qr_card_x + (qr_w / 2.0), qr_card_y + 14, "SCAN WITH PHONE CAMERA")

    # Circular Badge (INSTANT ACCESS)
    badge_x = qr_card_x + qr_w + 28
    badge_y = qr_card_y + (qr_h / 2.0)
    c.setFillColor(FOREST_GREEN)
    c.circle(badge_x, badge_y, 32, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setLineWidth(2)
    c.circle(badge_x, badge_y, 30, fill=0, stroke=1)

    c.setFillColor(MINT_GREEN)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(badge_x, badge_y + 7, "INSTANT")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.white)
    c.drawCentredString(badge_x, badge_y - 6, "ACCESS")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(MINT_GREEN)
    c.drawCentredString(badge_x, badge_y - 16, "24 / 7")

    # 5. Prominent Digital Barcode Notice for Students
    banner_y = qr_card_y - 56
    banner_h = 44
    c.setFillColor(colors.HexColor("#F0FDF4"))
    c.setStrokeColor(colors.HexColor("#86EFAC"))
    c.setLineWidth(1.5)
    c.roundRect(28, banner_y, width - 56, banner_h, 10, fill=1, stroke=1)

    # Barcode Icon Block
    c.setFillColor(FOREST_GREEN)
    c.roundRect(36, banner_y + 6, 32, 32, 6, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(MINT_GREEN)
    c.drawCentredString(52, banner_y + 14, "|||")

    # Barcode Banner Title
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(EMERALD)
    c.drawString(76, banner_y + 26, "DIGITAL LIBRARY BARCODE EMAILED TO ALL STUDENTS")

    # Barcode Banner Subtitle
    c.setFont("Helvetica", 7.8)
    c.setFillColor(colors.HexColor("#166534"))
    c.drawString(76, banner_y + 14, "Check your SRM email! Save your barcode image on your phone & show it at the desk for instant checkout.")

    # 6. Step-by-Step Instructions List
    step_start_y = banner_y - 28
    step_gap = 42
    steps = [
        ("1", "SCAN QR CODE OR OPEN WEBSITE", f"Access {display_url} on your phone, tablet, or laptop. No app download needed."),
        ("2", "BROWSE 2,100+ TEXTBOOKS & GATE PAPERS", "Search by book title, author, course code, or syllabus topic with real-time filters."),
        ("3", "CHECK LIVE SHELF AVAILABILITY", "View current shelf status and exact expected return dates before visiting the library."),
        ("4", "TRACK YOUR BORROWED BOOKS", "Enter your Register Number under 'Check My Books' to see active loans and return dues."),
        ("5", "QUICK ISSUE AT LIBRARIAN DESK", "Show your emailed digital barcode on your mobile for immediate barcode-scanned checkout.")
    ]

    for idx, (num, title, desc) in enumerate(steps):
        sy = step_start_y - (idx * step_gap)

        # Step Number Circle
        c.setFillColor(FOREST_GREEN)
        c.circle(46, sy + 6, 12, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(46, sy + 3, num)

        # Step Title
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(FOREST_GREEN)
        c.drawString(68, sy + 8, title)

        # Step Description
        c.setFont("Helvetica", 7.8)
        c.setFillColor(TEXT_MUTED)
        c.drawString(68, sy - 3, desc)

        # Separator line
        if idx < 4:
            c.setStrokeColor(BORDER_LIGHT)
            c.setLineWidth(0.6)
            c.line(68, sy - 11, width - 36, sy - 11)

    # 7. Help Box
    help_y = 86
    c.setFillColor(BG_CREAM)
    c.setStrokeColor(BORDER_LIGHT)
    c.setLineWidth(1)
    c.roundRect(28, help_y, width - 56, 30, 8, fill=1, stroke=1)

    c.setFillColor(FOREST_GREEN)
    c.circle(44, help_y + 15, 9, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(44, help_y + 12, "?")

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(FOREST_GREEN)
    c.drawString(60, help_y + 17, "NEED ASSISTANCE?")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(60, help_y + 7, "Ask the librarian at the desk or visit the Rules & Timings tab on the portal.")

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(SAGE_ACCENT)
    c.drawRightString(width - 40, help_y + 11, display_url)

    # 8. Footer Forest Green Bar
    footer_h = 52
    c.setFillColor(FOREST_GREEN)
    c.rect(26, 22, width - 52, footer_h, fill=1, stroke=0)

    # Top accent line
    c.setFillColor(MINT_GREEN)
    c.rect(26, 22 + footer_h - 2.5, width - 52, 2.5, fill=1, stroke=0)

    # Left: Department Info
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(colors.white)
    c.drawString(42, 54, "EEE DEPARTMENT LIBRARY")

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(MINT_GREEN)
    c.drawString(42, 42, "SRM INSTITUTE OF SCIENCE AND TECHNOLOGY")

    c.setFont("Times-Italic", 7.5)
    c.setFillColor(colors.HexColor("#CBD5E1"))
    c.drawString(42, 31, "Knowledge Drives Innovation")

    # Center Vertical Separator
    c.setStrokeColor(colors.HexColor("#334D3D"))
    c.setLineWidth(1)
    c.line(290, 26, 290, 68)

    # Right: Working Hours
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(colors.white)
    c.drawString(306, 56, "LIBRARY WORKING HOURS")

    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.drawString(306, 42, "Morning: 9:30 AM – 12:30 PM  |  Lunch: 12:30 – 1:30 PM")
    c.drawString(306, 30, "Afternoon: 1:30 PM – 4:30 PM")

    # Finish & Output
    c.showPage()
    c.save()

    if output_path:
        return None
    buffer.seek(0)
    return buffer.getvalue()


if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "srm_library_poster.pdf")
    build_poster_pdf("https://srm-eee-library.onrender.com", out_file)
    print(f"Generated website-themed poster PDF at: {out_file}")

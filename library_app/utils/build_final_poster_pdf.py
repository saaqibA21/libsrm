"""
Generates the final vector-crisp A4 print-ready PDF matching the approved poster design:
- Crisp white institutional header with SRM crest & EEE Department Library
- Deep forest green hero banner with elegant serif typography
- Pill badge with eeelibrary.org
- High-contrast scannable QR card with gold brackets & Instant Access medallion
- Emerald student barcode card with real barcode lines
- 4 clean modern feature cards (Scan QR, Browse Books, Live Availability, Instant Checkout)
- Accurate SRM EEE library working hours footer
"""

import io
import os
import qrcode
from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def build_final_pdf(output_path="srm_poster_final.pdf"):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4  # 595.27 x 841.89 points

    # Exact palette
    FOREST_GREEN = colors.HexColor("#122A1B")
    EMERALD_CARD = colors.HexColor("#065F46")
    EMERALD_LIGHT = colors.HexColor("#D1FAE5")
    MINT = colors.HexColor("#6EE7B7")
    GOLD = colors.HexColor("#D4AF37")
    GOLD_LIGHT = colors.HexColor("#FDE68A")
    CARD_BG = colors.HexColor("#FFFFFF")
    PAGE_BG = colors.HexColor("#F8FAF6")
    BORDER_SUBTLE = colors.HexColor("#E2E8F0")
    TEXT_DARK = colors.HexColor("#0F172A")
    TEXT_MUTED = colors.HexColor("#64748B")

    # 1. Base Page
    c.setFillColor(PAGE_BG)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # 2. Header Area
    header_h = 70
    header_y = height - header_h
    c.setFillColor(colors.white)
    c.rect(0, header_y, width, header_h, fill=1, stroke=0)

    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), "webapp", "static", "images", "srm_logo.png")
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 36, header_y + 12, width=46, height=46, mask="auto")

    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(FOREST_GREEN)
    c.drawString(90, header_y + 38, "SRM")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEXT_DARK)
    c.drawString(136, header_y + 41, "INSTITUTE OF SCIENCE & TECHNOLOGY")
    c.setFont("Helvetica", 6)
    c.setFillColor(TEXT_MUTED)
    c.drawString(136, header_y + 32, "(Deemed to be University u/s 3 of UGC Act, 1956)")

    # Vertical divider
    c.setStrokeColor(BORDER_SUBTLE)
    c.setLineWidth(1.2)
    c.line(285, header_y + 18, 285, header_y + 54)

    c.setFont("Helvetica-Bold", 13.5)
    c.setFillColor(FOREST_GREEN)
    c.drawString(300, header_y + 36, "EEE DEPARTMENT LIBRARY")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#334D3D"))
    c.drawString(300, header_y + 24, "DIGITAL LIBRARY & CATALOG PORTAL")

    # Bottom border of header
    c.setStrokeColor(BORDER_SUBTLE)
    c.line(0, header_y, width, header_y)

    # 3. Hero Forest Green Banner
    hero_h = 136
    hero_y = header_y - hero_h
    c.setFillColor(FOREST_GREEN)
    c.rect(0, hero_y, width, hero_h, fill=1, stroke=0)

    # Gold accent line on top of banner
    c.setFillColor(GOLD)
    c.rect(0, header_y - 3, width, 3, fill=1, stroke=0)

    # Headline
    c.setFont("Times-Bold", 22)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2.0, hero_y + 92, "ACCESS OUR DIGITAL LIBRARY —")

    c.setFont("Helvetica-Bold", 19)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2.0, hero_y + 68, "SCAN & GET STARTED")

    # Pill badge for eeelibrary.org
    pill_w = 210
    pill_h = 28
    pill_x = (width - pill_w) / 2.0
    pill_y = hero_y + 20
    c.setFillColor(colors.HexColor("#1A3A26"))
    c.roundRect(pill_x, pill_y, pill_w, pill_h, 14, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.roundRect(pill_x, pill_y, pill_w, pill_h, 14, fill=0, stroke=1)

    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(GOLD_LIGHT)
    c.drawCentredString(width / 2.0, pill_y + 8, "eeelibrary.org")

    # 4. Central QR Code Floating Card
    qr_card_w = 250
    qr_card_h = 240
    qr_card_x = (width - qr_card_w) / 2.0
    qr_card_y = hero_y - (qr_card_h * 0.62)

    # Card shadow
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.roundRect(qr_card_x + 4, qr_card_y - 4, qr_card_w, qr_card_h, 18, fill=1, stroke=0)

    # Card body
    c.setFillColor(colors.white)
    c.setStrokeColor(BORDER_SUBTLE)
    c.setLineWidth(1.5)
    c.roundRect(qr_card_x, qr_card_y, qr_card_w, qr_card_h, 18, fill=1, stroke=1)

    # Generate QR Code for eeelibrary.org
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data("https://eeelibrary.org")
    qr.make(fit=True)
    qr_pil = qr.make_image(fill_color="#122A1B", back_color="white").convert("RGB")
    temp_qr = "temp_final_qr.png"
    qr_pil.save(temp_qr)

    qr_size = 170
    qr_img_x = (width - qr_size) / 2.0
    qr_img_y = qr_card_y + 44
    c.drawImage(temp_qr, qr_img_x, qr_img_y, width=qr_size, height=qr_size)
    try: os.remove(temp_qr)
    except: pass

    # Gold corner brackets around QR code
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.8)
    bl = 22
    # TL
    c.line(qr_img_x - 10, qr_img_y + qr_size + 10, qr_img_x - 10 + bl, qr_img_y + qr_size + 10)
    c.line(qr_img_x - 10, qr_img_y + qr_size + 10, qr_img_x - 10, qr_img_y + qr_size + 10 - bl)
    # TR
    c.line(qr_img_x + qr_size + 10, qr_img_y + qr_size + 10, qr_img_x + qr_size + 10 - bl, qr_img_y + qr_size + 10)
    c.line(qr_img_x + qr_size + 10, qr_img_y + qr_size + 10, qr_img_x + qr_size + 10, qr_img_y + qr_size + 10 - bl)
    # BL
    c.line(qr_img_x - 10, qr_img_y - 10, qr_img_x - 10 + bl, qr_img_y - 10)
    c.line(qr_img_x - 10, qr_img_y - 10, qr_img_x - 10, qr_img_y - 10 + bl)
    # BR
    c.line(qr_img_x + qr_size + 10, qr_img_y - 10, qr_img_x + qr_size + 10 - bl, qr_img_y - 10)
    c.line(qr_img_x + qr_size + 10, qr_img_y - 10, qr_img_x + qr_size + 10, qr_img_y - 10 + bl)

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(FOREST_GREEN)
    c.drawCentredString(width / 2.0, qr_card_y + 18, "SCAN WITH YOUR PHONE CAMERA")

    # Gold Medallion Badge (INSTANT ACCESS 24/7)
    seal_x = qr_card_x + qr_card_w + 34
    seal_y = qr_card_y + (qr_card_h / 2.0)
    c.setFillColor(GOLD)
    c.circle(seal_x, seal_y, 36, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#B8860B"))
    c.circle(seal_x, seal_y, 33, fill=1, stroke=0)
    c.setFillColor(GOLD_LIGHT)
    c.circle(seal_x, seal_y, 31, fill=1, stroke=0)

    c.setFillColor(FOREST_GREEN)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(seal_x, seal_y + 11, "INSTANT ACCESS")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(seal_x, seal_y - 5, "24/7")

    # 5. Student Digital Barcode Card Banner
    bc_card_w = width - 72
    bc_card_h = 66
    bc_card_x = 36
    bc_card_y = qr_card_y - 82

    # Card background
    c.setFillColor(EMERALD_CARD)
    c.roundRect(bc_card_x, bc_card_y, bc_card_w, bc_card_h, 12, fill=1, stroke=0)

    # Mini Barcode graphic box
    c.setFillColor(colors.white)
    c.roundRect(bc_card_x + 12, bc_card_y + 9, 68, 48, 6, fill=1, stroke=0)

    # Draw vertical barcode lines
    c.setFillColor(colors.HexColor("#1A202C"))
    line_x = bc_card_x + 18
    import random
    random.seed(99)
    while line_x < bc_card_x + 74:
        bw = random.choice([1.2, 1.8, 2.5, 3.5])
        c.rect(line_x, bc_card_y + 15, bw, 34, fill=1, stroke=0)
        line_x += bw + random.choice([1.2, 2.0, 2.8])

    # Text in barcode banner
    c.setFont("Helvetica-Bold", 11.5)
    c.setFillColor(GOLD_LIGHT)
    c.drawString(bc_card_x + 90, bc_card_y + 40, "DIGITAL BARCODE SENT TO STUDENT EMAIL —")

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.white)
    c.drawString(bc_card_x + 90, bc_card_y + 24, "Check your SRM email! Save or show your barcode on mobile for 5-sec desk checkout.")

    c.setFont("Helvetica", 7.5)
    c.setFillColor(MINT)
    c.drawString(bc_card_x + 90, bc_card_y + 11, "No physical card required • Instant barcode scanning at the library desk")

    # 6. 4 Modern Feature Cards (Grid 4 Columns)
    cards_y = bc_card_y - 100
    card_w = (width - 72 - 36) / 4.0  # 4 equal columns
    card_h = 82

    cards_info = [
        ("1. Scan QR", "or visit", "eeelibrary.org"),
        ("2. Browse Books", "2,100+ Books &", "GATE Papers"),
        ("3. Check Live", "Availability", "24/7 Online"),
        ("4. Instant Issue", "Show Barcode", "at Desk")
    ]

    for idx, (title, l1, l2) in enumerate(cards_info):
        cx = 36 + idx * (card_w + 12)

        # Card shadow & body
        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.roundRect(cx + 2, cards_y - 2, card_w, card_h, 10, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setStrokeColor(BORDER_SUBTLE)
        c.setLineWidth(1)
        c.roundRect(cx, cards_y, card_w, card_h, 10, fill=1, stroke=1)

        # Gold top accent
        c.setFillColor(GOLD)
        c.roundRect(cx, cards_y + card_h - 4, card_w, 4, 2, fill=1, stroke=0)

        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(FOREST_GREEN)
        c.drawCentredString(cx + (card_w / 2.0), cards_y + 54, title)

        c.setFont("Helvetica", 8)
        c.setFillColor(TEXT_MUTED)
        c.drawCentredString(cx + (card_w / 2.0), cards_y + 36, l1)
        c.drawCentredString(cx + (card_w / 2.0), cards_y + 22, l2)

    # 7. Institutional Footer Bar
    footer_h = 42
    footer_y = 0
    c.setFillColor(FOREST_GREEN)
    c.rect(0, footer_y, width, footer_h, fill=1, stroke=0)

    # Gold line on top of footer
    c.setFillColor(GOLD)
    c.rect(0, footer_h - 2, width, 2, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(colors.white)
    c.drawString(36, 17, "SRM INSTITUTE OF SCIENCE AND TECHNOLOGY  •  EEE DEPARTMENT LIBRARY")

    hours_text = "Working Hours: Mon – Fri: 8:30 AM – 5:00 PM  |  Sat: 9:00 AM – 1:00 PM"
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(GOLD_LIGHT)
    c.drawRightString(width - 36, 17, hours_text)

    # Save
    c.showPage()
    c.save()
    print(f"Generated final vector PDF poster at: {output_path}")

if __name__ == "__main__":
    build_final_pdf("srm_poster_final.pdf")

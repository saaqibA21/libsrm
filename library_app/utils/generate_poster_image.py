"""
Premium Luxury Poster Generator for SRM EEE Department Library (eeelibrary.org).
Renders an ultra high-resolution (1800 x 2545 px, 300 DPI) masterpiece poster:
- Deep British racing forest green (#0E2316 to #16321F)
- Elegant gold trim (#D4AF37)
- Real SRM emblem logo
- Live scannable QR code for eeelibrary.org
- Dedicated Digital Barcode Card graphic for student checkout
- Clean academic layout & typography
"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def render_premium_poster(target_url="https://eeelibrary.org"):
    width, height = 1800, 2545
    
    # Gradient Dark Forest Green Background
    img = Image.new("RGB", (width, height), (14, 35, 22))
    draw = ImageDraw.Draw(img)

    # Color Palette
    DARK_FOREST = (14, 35, 22)       # #0E2316
    PINE_GREEN = (22, 50, 31)        # #16321F
    CARD_GREEN = (18, 43, 27)        # #122B1B
    GOLD = (212, 175, 55)            # #D4AF37
    GOLD_LIGHT = (245, 222, 126)     # #F5DE7E
    MINT_GREEN = (134, 239, 172)     # #86EFAC
    WHITE = (255, 255, 255)
    CREAM = (244, 246, 241)
    TEXT_MUTED = (160, 185, 168)

    # System fonts
    def get_font(name, size, fallback="arial.ttf"):
        paths = [
            f"C:\\Windows\\Fonts\\{name}",
            f"C:\\Windows\\Fonts\\{fallback}",
            "arial.ttf"
        ]
        for p in paths:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except Exception: pass
        return ImageFont.load_default()

    font_univ = get_font("georgiab.ttf", 46)
    font_univ_sub = get_font("segoeuib.ttf", 20)
    font_univ_deemed = get_font("segoeui.ttf", 15)
    font_dept = get_font("segoeuib.ttf", 36)
    font_dept_sub = get_font("segoeuib.ttf", 22)

    font_title_main = get_font("georgiab.ttf", 64)
    font_title_sub = get_font("segoeuib.ttf", 48)
    font_url = get_font("consolab.ttf", 36)

    font_card_head = get_font("segoeuib.ttf", 30)
    font_card_desc = get_font("segoeui.ttf", 22)
    font_step_num = get_font("georgiab.ttf", 34)
    font_step_title = get_font("segoeuib.ttf", 28)
    font_step_sub = get_font("segoeui.ttf", 21)
    font_footer = get_font("segoeui.ttf", 21)

    # Background subtle radial/linear depth
    for y in range(0, 900):
        factor = y / 900.0
        r = int(14 + factor * 8)
        g = int(35 + factor * 15)
        b = int(22 + factor * 9)
        draw.line((0, y, width, y), fill=(r, g, b))

    # Top Header White Container Card
    header_h = 160
    draw.rectangle([0, 0, width, header_h], fill=WHITE)
    draw.rectangle([0, header_h - 4, width, header_h], fill=GOLD)

    # Logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "webapp", "static", "images", "srm_logo.png")
    if os.path.exists(logo_path):
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_img = logo_img.resize((110, 110), Image.Resampling.LANCZOS)
        img.paste(logo_img, (80, 25), logo_img)

    draw.text((215, 25), "SRM", fill=(14, 35, 22), font=font_univ)
    draw.text((345, 34), "INSTITUTE OF SCIENCE & TECHNOLOGY", fill=(20, 30, 20), font=font_univ_sub)
    draw.text((345, 68), "(Deemed to be University u/s 3 of UGC Act, 1956)", fill=(90, 105, 95), font=font_univ_deemed)

    # Vertical divider
    draw.line([(910, 25), (910, 135)], fill=(215, 225, 215), width=2)

    draw.text((945, 35), "EEE DEPARTMENT", fill=(14, 35, 22), font=font_dept)
    draw.text((945, 85), "DEPARTMENT LIBRARY", fill=(60, 95, 70), font=font_dept_sub)

    # Gold Accent Horizontal Lines
    draw.line([(80, 210), (width - 80, 210)], fill=GOLD, width=3)
    draw.line([(80, 218), (width - 80, 218)], fill=(80, 120, 90), width=1)

    # Main Headline in Luxury Serif
    draw.text((width // 2, 290), "ACCESS OUR DIGITAL LIBRARY —", fill=WHITE, font=font_title_main, anchor="mm")
    draw.text((width // 2, 368), "SCAN & GET STARTED", fill=MINT_GREEN, font=font_title_sub, anchor="mm")

    # URL Pill Badge
    url_text = target_url.replace("https://", "").replace("http://", "").rstrip("/")
    pill_w = 460
    pill_rect = [(width // 2) - (pill_w // 2), 430, (width // 2) + (pill_w // 2), 498]
    draw.rounded_rectangle(pill_rect, radius=34, fill=WHITE, outline=GOLD, width=3)
    draw.text((width // 2, 464), f"🌐  {url_text}", fill=DARK_FOREST, font=font_url, anchor="mm")

    # Center QR Code Floating Card
    qr_card_w, qr_card_h = 560, 560
    qr_cx = (width - qr_card_w) // 2
    qr_cy = 550

    # Glow & Shadow
    for i in range(8, 0, -2):
        draw.rounded_rectangle([qr_cx - i, qr_cy - i, qr_cx + qr_card_w + i, qr_cy + qr_card_h + i], radius=36, fill=(8, 22, 14))
    draw.rounded_rectangle([qr_cx, qr_cy, qr_cx + qr_card_w, qr_cy + qr_card_h], radius=32, fill=WHITE)

    # Scannable QR code
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=1)
    qr.add_data(target_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0E2316", back_color="white").convert("RGB")
    qr_img = qr_img.resize((410, 410), Image.Resampling.LANCZOS)
    img.paste(qr_img, (qr_cx + 75, qr_cy + 50))

    # Corner brackets
    bw, bl = 6, 48
    # TL
    draw.line((qr_cx + 45, qr_cy + 25, qr_cx + 45 + bl, qr_cy + 25), fill=DARK_FOREST, width=bw)
    draw.line((qr_cx + 45, qr_cy + 25, qr_cx + 45, qr_cy + 25 + bl), fill=DARK_FOREST, width=bw)
    # TR
    draw.line((qr_cx + qr_card_w - 45, qr_cy + 25, qr_cx + qr_card_w - 45 - bl, qr_cy + 25), fill=DARK_FOREST, width=bw)
    draw.line((qr_cx + qr_card_w - 45, qr_cy + 25, qr_cx + qr_card_w - 45, qr_cy + 25 + bl), fill=DARK_FOREST, width=bw)
    # BL
    draw.line((qr_cx + 45, qr_cy + qr_card_h - 75, qr_cx + 45 + bl, qr_cy + qr_card_h - 75), fill=DARK_FOREST, width=bw)
    draw.line((qr_cx + 45, qr_cy + qr_card_h - 75, qr_cx + 45, qr_cy + qr_card_h - 75 - bl), fill=DARK_FOREST, width=bw)
    # BR
    draw.line((qr_cx + qr_card_w - 45, qr_cy + qr_card_h - 75, qr_cx + qr_card_w - 45 - bl, qr_cy + qr_card_h - 75), fill=DARK_FOREST, width=bw)
    draw.line((qr_cx + qr_card_w - 45, qr_cy + qr_card_h - 75, qr_cx + qr_card_w - 45, qr_cy + qr_card_h - 75 - bl), fill=DARK_FOREST, width=bw)

    draw.text((width // 2, qr_cy + qr_card_h - 38), "📷  SCAN WITH YOUR PHONE CAMERA", fill=DARK_FOREST, font=get_font("segoeuib.ttf", 22), anchor="mm")

    # Gold Circular Badge (INSTANT ACCESS)
    badge_x = qr_cx + qr_card_w + 55
    badge_y = qr_cy + (qr_card_h // 2) - 40
    br = 95
    draw.ellipse([badge_x - br, badge_y - br, badge_x + br, badge_y + br], fill=GOLD, outline=GOLD_LIGHT, width=5)
    draw.ellipse([badge_x - br + 8, badge_y - br + 8, badge_x + br - 8, badge_y + br - 8], fill=(185, 145, 35))
    draw.text((badge_x, badge_y - 20), "INSTANT", fill=WHITE, font=get_font("segoeuib.ttf", 26), anchor="mm")
    draw.text((badge_x, badge_y + 14), "ACCESS", fill=WHITE, font=get_font("segoeuib.ttf", 26), anchor="mm")
    draw.text((badge_x, badge_y + 44), "★ 24 / 7 ★", fill=GOLD_LIGHT, font=get_font("segoeuib.ttf", 16), anchor="mm")

    # 4. Student Digital Barcode Spotlight Card
    card_y = qr_cy + qr_card_h + 45
    card_h = 240
    card_rect = [80, card_y, width - 80, card_y + card_h]

    # Glow border
    draw.rounded_rectangle([76, card_y - 4, width - 76, card_y + card_h + 4], radius=28, fill=CARD_GREEN, outline=GOLD, width=3)

    # Left: Mini Student Card Graphic
    mini_w, mini_h = 270, 160
    mini_x = 120
    mini_y = card_y + 40
    draw.rounded_rectangle([mini_x, mini_y, mini_x + mini_w, mini_y + mini_h], radius=14, fill=WHITE)
    # Header strip of mini card
    draw.rounded_rectangle([mini_x, mini_y, mini_x + mini_w, mini_y + 36], radius=14, fill=DARK_FOREST)
    draw.rectangle([mini_x, mini_y + 24, mini_x + mini_w, mini_y + 36], fill=DARK_FOREST)
    draw.text((mini_x + (mini_w // 2), mini_y + 18), "SRM DIGITAL LIBRARY CARD", fill=WHITE, font=get_font("segoeuib.ttf", 13), anchor="mm")

    # Barcode bars illustration inside mini card
    bar_y = mini_y + 48
    bar_h = 58
    import random
    random.seed(42)
    bx = mini_x + 22
    while bx < mini_x + mini_w - 22:
        bw = random.choice([2, 3, 5, 7])
        draw.rectangle([bx, bar_y, bx + bw, bar_y + bar_h], fill=(20, 20, 20))
        bx += bw + random.choice([2, 3, 4])
    draw.text((mini_x + (mini_w // 2), mini_y + 130), "* RA2111005010042 *", fill=(60, 60, 60), font=get_font("consolab.ttf", 14), anchor="mm")

    # Right: Callout Text
    text_x = 430
    draw.text((text_x, card_y + 42), "DIGITAL BARCODE CARD SENT TO STUDENT EMAIL", fill=GOLD_LIGHT, font=font_card_head)
    
    desc_line1 = "Check your registered SRM student inbox! Every student has been issued an official"
    desc_line2 = "Digital Barcode Card. Simply save the barcode on your phone & present it at the"
    desc_line3 = "librarian desk for instant 5-second book checkout — no physical card required!"
    draw.text((text_x, card_y + 92), desc_line1, fill=WHITE, font=font_card_desc)
    draw.text((text_x, card_y + 126), desc_line2, fill=WHITE, font=font_card_desc)
    draw.text((text_x, card_y + 160), desc_line3, fill=MINT_GREEN, font=font_card_desc)

    # 5. 4 Clear Action Steps (2 x 2 Clean Grid)
    steps_y = card_y + card_h + 50
    step_items = [
        ("1", "Scan QR Code or Open Site", f"Open {url_text} instantly on any mobile, tablet, or laptop."),
        ("2", "Browse 2,100+ Department Books", "Search textbooks, GATE materials & syllabus copies by title or author."),
        ("3", "Check Live Availability 24/7", "View real-time shelf status & expected return dates before visiting."),
        ("4", "Instant Checkout at Desk", "Show your emailed digital barcode for immediate scanned checkout.")
    ]

    col_w = (width - 240) // 2
    for idx, (num, title, sub) in enumerate(step_items):
        col = idx % 2
        row = idx // 2
        sx = 120 + (col * (col_w + 60))
        sy = steps_y + (row * 125)

        # Number circle in gold/mint
        draw.ellipse([sx, sy + 6, sx + 56, sy + 62], fill=CARD_GREEN, outline=GOLD, width=3)
        draw.text((sx + 28, sy + 34), num, fill=GOLD_LIGHT, font=font_step_num, anchor="mm")

        # Step Text
        draw.text((sx + 74, sy + 8), title, fill=WHITE, font=font_step_title)
        draw.text((sx + 74, sy + 46), sub, fill=TEXT_MUTED, font=font_step_sub)

    # Gold Accent Bottom Line
    draw.line([(80, height - 160), (width - 80, height - 160)], fill=GOLD, width=2)

    # Footer Information
    draw.text((80, height - 120), "EEE DEPARTMENT LIBRARY  •  SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", fill=WHITE, font=get_font("segoeuib.ttf", 24))
    draw.text((80, height - 80), "Knowledge Drives Innovation  |  Location: Department of EEE, SRMIST", fill=TEXT_MUTED, font=font_footer)

    hours_str = "Working Hours: 9:30 AM – 12:30 PM & 1:30 PM – 4:30 PM (Mon – Fri)"
    draw.text((width - 80, height - 120), hours_str, fill=MINT_GREEN, font=get_font("segoeuib.ttf", 22), anchor="ra")
    draw.text((width - 80, height - 80), f"Digital Portal: {url_text}", fill=GOLD_LIGHT, font=font_footer, anchor="ra")

    # Save PNG and JPG
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    png_path = os.path.join(root_dir, "srm_eeelibrary_poster.png")
    jpg_path = os.path.join(root_dir, "srm_eeelibrary_poster.jpg")

    img.save(png_path, "PNG", dpi=(300, 300))
    img.save(jpg_path, "JPEG", quality=98, dpi=(300, 300))

    artifact_dir = r"C:\Users\SAAQIB\.gemini\antigravity\brain\b5d23dad-cf09-42a8-84ab-0c10f7ac0ffd"
    if os.path.exists(artifact_dir):
        img.save(os.path.join(artifact_dir, "srm_eeelibrary_poster.png"), "PNG")

    print("Successfully rendered premium poster images.")

if __name__ == "__main__":
    render_premium_poster("https://eeelibrary.org")

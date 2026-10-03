"""
Generates ultra high-resolution (1800 x 2545 px, 300 DPI quality) printable poster images
for SRM EEE Department Library featuring eeelibrary.org and student barcode notice.
Outputs:
- srm_eeelibrary_poster.png (Lossless high-res)
- srm_eeelibrary_poster.jpg (Standard printable image)
"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def render_poster_image(target_url="https://eeelibrary.org"):
    # Output canvas: 1800 x 2545 px (standard A4 ratio 1:1.414)
    width, height = 1800, 2545
    img = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Color Palette matching website
    FOREST_GREEN = (28, 48, 34)      # #1C3022
    SAGE_ACCENT = (72, 99, 78)       # #48634E
    MINT_GREEN = (134, 239, 172)     # #86EFAC
    EMERALD_DARK = (20, 83, 45)      # #14532D
    EMERALD_BG = (240, 253, 244)     # #F0FDF4
    EMERALD_BORDER = (134, 239, 172) # #86EFAC
    BG_CREAM = (244, 246, 241)       # #F4F6F1
    TEXT_DARK = (23, 36, 26)         # #17241A
    TEXT_MUTED = (87, 104, 90)       # #57685A
    BORDER_LIGHT = (220, 229, 216)   # #DCE5D8
    WHITE = (255, 255, 255)

    # Load Windows system fonts
    def get_font(name, size, fallback="arial.ttf"):
        font_paths = [
            f"C:\\Windows\\Fonts\\{name}",
            f"C:\\Windows\\Fonts\\{fallback}",
            "arial.ttf"
        ]
        for p in font_paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    font_univ_title = get_font("georgiab.ttf", 52)
    font_univ_sub = get_font("segoeuib.ttf", 22)
    font_univ_deemed = get_font("segoeui.ttf", 17)
    font_dept_title = get_font("segoeuib.ttf", 38)
    font_dept_sub = get_font("segoeuib.ttf", 24)

    font_hero_pre = get_font("segoeuib.ttf", 20)
    font_hero_main = get_font("georgiab.ttf", 66)
    font_hero_sub = get_font("segoeuib.ttf", 50)
    font_hero_url = get_font("consolab.ttf", 36)

    font_qr_cap = get_font("segoeuib.ttf", 22)
    font_badge_bold = get_font("segoeuib.ttf", 24)
    font_badge_sub = get_font("segoeuib.ttf", 19)

    font_callout_title = get_font("segoeuib.ttf", 30)
    font_callout_desc = get_font("segoeui.ttf", 23)

    font_step_num = get_font("segoeuib.ttf", 30)
    font_step_title = get_font("segoeuib.ttf", 27)
    font_step_desc = get_font("segoeui.ttf", 22)

    font_help_title = get_font("segoeuib.ttf", 24)
    font_help_desc = get_font("segoeui.ttf", 21)
    font_footer_main = get_font("segoeuib.ttf", 28)
    font_footer_sub = get_font("segoeuib.ttf", 22)
    font_footer_hours = get_font("segoeui.ttf", 20)

    # 1. Header Area
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "webapp", "static", "images", "srm_logo.png")
    if os.path.exists(logo_path):
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_img = logo_img.resize((120, 120), Image.Resampling.LANCZOS)
        img.paste(logo_img, (80, 50), logo_img)

    # University title text
    draw.text((220, 50), "SRM", fill=FOREST_GREEN, font=font_univ_title)
    draw.text((360, 58), "INSTITUTE OF SCIENCE & TECHNOLOGY", fill=TEXT_DARK, font=font_univ_sub)
    draw.text((360, 92), "(Deemed to be University u/s 3 of UGC Act, 1956)", fill=TEXT_MUTED, font=font_univ_deemed)

    # Vertical divider line
    draw.line((880, 48, 880, 170), fill=BORDER_LIGHT, width=3)

    # Department title
    draw.text((920, 60), "EEE DEPARTMENT", fill=FOREST_GREEN, font=font_dept_title)
    draw.text((920, 110), "DEPARTMENT LIBRARY", fill=SAGE_ACCENT, font=font_dept_sub)

    # 2. Hero Dark Forest Green Banner
    hero_top = 195
    hero_h = 390
    hero_rect = [60, hero_top, width - 60, hero_top + hero_h]
    draw.rectangle(hero_rect, fill=FOREST_GREEN)

    # Pretitle pill
    draw.rounded_rectangle([(width // 2) - 220, hero_top + 28, (width // 2) + 220, hero_top + 72], radius=22, fill=(39, 66, 47))
    draw.text((width // 2, hero_top + 50), "OFFICIAL DEPARTMENT PORTAL", fill=MINT_GREEN, font=font_hero_pre, anchor="mm")

    # Main Headline
    draw.text((width // 2, hero_top + 130), "ACCESS OUR DIGITAL LIBRARY —", fill=WHITE, font=font_hero_main, anchor="mm")
    draw.text((width // 2, hero_top + 208), "SCAN & GET STARTED", fill=MINT_GREEN, font=font_hero_sub, anchor="mm")

    # URL Pill (Displaying eeelibrary.org)
    url_text = target_url.replace("https://", "").replace("http://", "").rstrip("/")
    url_pill_w = 480
    url_pill_rect = [(width // 2) - (url_pill_w // 2), hero_top + 275, (width // 2) + (url_pill_w // 2), hero_top + 345]
    draw.rounded_rectangle(url_pill_rect, radius=35, fill=WHITE)
    draw.text((width // 2, hero_top + 310), f"🌐  {url_text}", fill=FOREST_GREEN, font=font_hero_url, anchor="mm")

    # 3. Center QR Code Card
    qr_w, qr_h = 490, 490
    qr_x = (width - qr_w) // 2
    qr_y = hero_top + hero_h - 130

    # Card background & border
    draw.rounded_rectangle([qr_x + 6, qr_y + 6, qr_x + qr_w + 6, qr_y + qr_h + 6], radius=32, fill=(210, 220, 210))
    draw.rounded_rectangle([qr_x, qr_y, qr_x + qr_w, qr_y + qr_h], radius=32, fill=WHITE, outline=BORDER_LIGHT, width=4)

    # Generate QR Code image
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=1)
    qr.add_data(target_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1C3022", back_color="white").convert("RGB")
    qr_img = qr_img.resize((370, 370), Image.Resampling.LANCZOS)
    img.paste(qr_img, (qr_x + 60, qr_y + 45))

    # Corner brackets for scanning frame
    bw, bl = 6, 42
    # Top Left
    draw.line((qr_x + 40, qr_y + 25, qr_x + 40 + bl, qr_y + 25), fill=FOREST_GREEN, width=bw)
    draw.line((qr_x + 40, qr_y + 25, qr_x + 40, qr_y + 25 + bl), fill=FOREST_GREEN, width=bw)
    # Top Right
    draw.line((qr_x + qr_w - 40, qr_y + 25, qr_x + qr_w - 40 - bl, qr_y + 25), fill=FOREST_GREEN, width=bw)
    draw.line((qr_x + qr_w - 40, qr_y + 25, qr_x + qr_w - 40, qr_y + 25 + bl), fill=FOREST_GREEN, width=bw)
    # Bottom Left
    draw.line((qr_x + 40, qr_y + qr_h - 65, qr_x + 40 + bl, qr_y + qr_h - 65), fill=FOREST_GREEN, width=bw)
    draw.line((qr_x + 40, qr_y + qr_h - 65, qr_x + 40, qr_y + qr_h - 65 - bl), fill=FOREST_GREEN, width=bw)
    # Bottom Right
    draw.line((qr_x + qr_w - 40, qr_y + qr_h - 65, qr_x + qr_w - 40 - bl, qr_y + qr_h - 65), fill=FOREST_GREEN, width=bw)
    draw.line((qr_x + qr_w - 40, qr_y + qr_h - 65, qr_x + qr_w - 40, qr_y + qr_h - 65 - bl), fill=FOREST_GREEN, width=bw)

    draw.text((width // 2, qr_y + qr_h - 32), "📷  SCAN WITH YOUR PHONE CAMERA", fill=FOREST_GREEN, font=font_qr_cap, anchor="mm")

    # Circular Badge (INSTANT ACCESS)
    badge_cx = qr_x + qr_w + 50
    badge_cy = qr_y + (qr_h // 2)
    br = 92
    draw.ellipse([badge_cx - br, badge_cy - br, badge_cx + br, badge_cy + br], fill=FOREST_GREEN, outline=WHITE, width=6)
    draw.text((badge_cx, badge_cy - 22), "INSTANT", fill=MINT_GREEN, font=font_badge_bold, anchor="mm")
    draw.text((badge_cx, badge_cy + 12), "ACCESS", fill=WHITE, font=font_badge_bold, anchor="mm")
    draw.text((badge_cx, badge_cy + 42), "24 / 7", fill=MINT_GREEN, font=font_badge_sub, anchor="mm")

    # 4. Prominent Digital Barcode Notice for Students
    callout_top = qr_y + qr_h + 38
    callout_h = 138
    callout_rect = [70, callout_top, width - 70, callout_top + callout_h]
    draw.rounded_rectangle(callout_rect, radius=24, fill=EMERALD_BG, outline=EMERALD_BORDER, width=4)

    # Barcode Icon Badge
    draw.rounded_rectangle([95, callout_top + 18, 195, callout_top + 118], radius=18, fill=FOREST_GREEN)
    draw.text((145, callout_top + 68), "||||||", fill=MINT_GREEN, font=font_step_num, anchor="mm")

    draw.text((225, callout_top + 34), "DIGITAL LIBRARY BARCODE EMAILED TO ALL STUDENTS", fill=EMERALD_DARK, font=font_callout_title)
    draw.text((225, callout_top + 80), "Check your SRM email! Save or screenshot the barcode on your phone & show it at the desk for instant 5-second checkout.", fill=(22, 101, 52), font=font_callout_desc)

    # 5. 5-Step Instructions
    steps_top = callout_top + callout_h + 36
    step_gap = 130
    steps = [
        ("1", "SCAN QR CODE OR OPEN WEBSITE", f"Open {url_text} directly on your mobile, tablet, or laptop. No mobile app download needed."),
        ("2", "BROWSE 2,100+ TEXTBOOKS & GATE PAPERS", "Search by textbook title, author, course code, or syllabus topic with live instant search."),
        ("3", "CHECK LIVE AVAILABILITY 24/7", "View real-time shelf status, copies available, and exact expected return dates before visiting."),
        ("4", "TRACK YOUR ACTIVE BORROWED BOOKS", "Click 'Check My Books' and enter your Register Number to see currently borrowed books & dues."),
        ("5", "INSTANT ISSUE AT LIBRARIAN DESK", "Show your emailed digital barcode on your mobile to the librarian for immediate scanned checkout.")
    ]

    for idx, (num, title, desc) in enumerate(steps):
        sy = steps_top + (idx * step_gap)

        # Number circle
        draw.ellipse([110, sy, 174, sy + 64], fill=FOREST_GREEN)
        draw.text((142, sy + 32), num, fill=WHITE, font=font_step_num, anchor="mm")

        # Step Title
        draw.text((205, sy + 6), title, fill=FOREST_GREEN, font=font_step_title)
        draw.text((205, sy + 44), desc, fill=TEXT_MUTED, font=font_step_desc)

        # Separator Line
        if idx < 4:
            draw.line((205, sy + 92, width - 90, sy + 92), fill=BORDER_LIGHT, width=2)

    # 6. Help Info Strip
    help_top = height - 250
    help_h = 75
    draw.rounded_rectangle([70, help_top, width - 70, help_top + help_h], radius=16, fill=BG_CREAM, outline=BORDER_LIGHT, width=2)
    draw.ellipse([92, help_top + 16, 136, help_top + 60], fill=FOREST_GREEN)
    draw.text((114, help_top + 38), "?", fill=WHITE, font=font_help_title, anchor="mm")

    draw.text((155, help_top + 22), "NEED HELP?", fill=FOREST_GREEN, font=font_help_title)
    draw.text((155, help_top + 50), "Visit the library portal on your mobile or ask the librarian at the desk.", fill=TEXT_MUTED, font=font_help_desc)
    draw.text((width - 95, help_top + 38), url_text, fill=SAGE_ACCENT, font=font_help_title, anchor="rm")

    # 7. Institutional Footer Bar
    footer_h = 140
    footer_top = height - footer_h
    draw.rectangle([0, footer_top, width, height], fill=FOREST_GREEN)
    draw.rectangle([0, footer_top, width, footer_top + 6], fill=MINT_GREEN)

    draw.text((80, footer_top + 34), "EEE DEPARTMENT LIBRARY", fill=WHITE, font=font_footer_main)
    draw.text((80, footer_top + 72), "SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", fill=MINT_GREEN, font=font_footer_sub)
    draw.text((80, footer_top + 104), "Knowledge Drives Innovation", fill=(203, 213, 225), font=font_univ_deemed)

    draw.line((940, footer_top + 20, 940, height - 20), fill=(51, 77, 61), width=2)

    draw.text((980, footer_top + 34), "LIBRARY WORKING HOURS", fill=WHITE, font=font_footer_main)
    draw.text((980, footer_top + 70), "Monday – Friday: 8:30 AM – 5:00 PM  |  Saturday: 9:00 AM – 1:00 PM", fill=WHITE, font=font_footer_hours)
    draw.text((980, footer_top + 102), "Closed on Sundays & University Holidays", fill=(148, 163, 184), font=font_univ_deemed)

    # Save PNG and JPG
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    png_path = os.path.join(root_dir, "srm_eeelibrary_poster.png")
    jpg_path = os.path.join(root_dir, "srm_eeelibrary_poster.jpg")

    img.save(png_path, "PNG", dpi=(300, 300))
    img.save(jpg_path, "JPEG", quality=96, dpi=(300, 300))

    # Also copy to artifacts directory for chat embedding
    artifact_dir = r"C:\Users\SAAQIB\.gemini\antigravity\brain\b5d23dad-cf09-42a8-84ab-0c10f7ac0ffd"
    if os.path.exists(artifact_dir):
        artifact_png = os.path.join(artifact_dir, "srm_eeelibrary_poster.png")
        img.save(artifact_png, "PNG")

    print(f"Generated high-res poster images:\n - {png_path}\n - {jpg_path}")
    return png_path

if __name__ == "__main__":
    render_poster_image("https://eeelibrary.org")

import os
import io
import qrcode
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_no_due_certificate_pdf(patron: dict, cert_date: str = None, cert_id: str = None) -> bytes:
    """
    Generate the official vector-crisp A4 Landscape No Due Certificate PDF
    matching the SRM EEE Department Library institutional template.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    w, h = landscape(A4)  # 841.89 x 595.27 pt

    if not cert_date:
        cert_date = datetime.now().strftime("%d-%m-%Y")
    if not cert_id:
        cert_id = f"SRM/EEE-LIB/NDC/{datetime.now().year}/{patron.get('id', 1):04d}"

    # Colors
    TEXT_BLACK = colors.HexColor("#111827")
    MUTED_GRAY = colors.HexColor("#4B5563")
    SRM_BLUE = colors.HexColor("#1A365D")
    BORDER_GRAY = colors.HexColor("#D1D5DB")
    SUCCESS_GREEN = colors.HexColor("#065F46")

    # Outer decorative certificate border
    c.setStrokeColor(BORDER_GRAY)
    c.setLineWidth(1)
    c.rect(24, 24, w - 48, h - 48)

    c.setStrokeColor(SRM_BLUE)
    c.setLineWidth(1.5)
    c.rect(28, 28, w - 56, h - 56)

    # 1. Header: SRM Institutional Banner
    banner_path = os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "static", "images", "srm_header_banner.png")
    if os.path.exists(banner_path):
        c.drawImage(banner_path, 48, h - 100, width=220, height=65, mask="auto")
    else:
        # Fallback crest
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "static", "images", "srm_logo.png")
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 48, h - 96, width=54, height=54, mask="auto")
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(SRM_BLUE)
        c.drawString(110, h - 68, "SRM")
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(TEXT_BLACK)
        c.drawString(160, h - 65, "INSTITUTE OF SCIENCE & TECHNOLOGY")
        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(MUTED_GRAY)
        c.drawString(160, h - 77, "(Deemed to be University u/s 3 of UGC Act, 1956)")

    # Right side of header: Reference ID and Verification
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(SRM_BLUE)
    c.drawRightString(w - 48, h - 58, "OFFICIAL LIBRARY CLEARANCE")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED_GRAY)
    c.drawRightString(w - 48, h - 72, f"Certificate No: {cert_id}")
    c.drawRightString(w - 48, h - 85, f"Issued Date: {cert_date}")

    # 2. Institutional Double Horizontal Line
    c.setStrokeColor(TEXT_BLACK)
    c.setLineWidth(1.0)
    c.line(48, h - 110, w - 48, h - 110)
    c.setLineWidth(2.5)
    c.line(48, h - 114, w - 48, h - 114)

    # 3. Main Heading: Bold and Underlined
    title_text = "EEE Department Library - No Due Certificate"
    c.setFont("Helvetica-Bold", 19)
    c.setFillColor(TEXT_BLACK)
    title_w = c.stringWidth(title_text, "Helvetica-Bold", 19)
    title_x = (w - title_w) / 2
    title_y = h - 170
    c.drawString(title_x, title_y, title_text)

    c.setLineWidth(1.5)
    c.line(title_x, title_y - 4, title_x + title_w, title_y - 4)

    # 4. Certificate Body Text
    name = (patron.get("name") or "STUDENT").strip().upper()
    reg_no = (patron.get("register_number") or patron.get("barcode") or "").strip().upper()
    ptype = (patron.get("patron_type") or "student").lower()
    is_staff = ptype in ("teacher", "faculty", "staff")

    salutation = "Mr./Ms." if not is_staff else ("Dr./Mr./Ms.")
    role_label = "Staff" if is_staff else "Student"

    # Department / Class string
    if is_staff:
        dept_str = patron.get("designation") or "Electrical and Electronics Engineering"
    else:
        year = patron.get("year", "")
        sec = patron.get("section", "")
        if year and sec:
            dept_str = f"EEE (Year {year} - Section {sec})"
        elif year:
            dept_str = f"EEE (Year {year})"
        else:
            dept_str = "Electrical and Electronics Engineering"

    # Text lines with prominent filled-in data
    body_y = h - 235
    line_spacing = 38

    # Line 1: This is to certify that Mr./Ms. [NAME]
    c.setFont("Helvetica", 14)
    c.setFillColor(TEXT_BLACK)
    c.drawString(58, body_y, f"This is to certify that {salutation}")

    name_start_x = 58 + c.stringWidth(f"This is to certify that {salutation} ", "Helvetica", 14)
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(SRM_BLUE)
    c.drawString(name_start_x, body_y, name)

    # Decorative solid underline for student name
    name_w = c.stringWidth(name, "Helvetica-Bold", 15)
    c.setStrokeColor(SRM_BLUE)
    c.setLineWidth(1.2)
    c.line(name_start_x, body_y - 3, name_start_x + name_w, body_y - 3)

    # Line 2: Library Member ID [REG]   Staff/Student of [DEPT] Department
    body_y -= line_spacing
    c.setFont("Helvetica", 14)
    c.setFillColor(TEXT_BLACK)
    c.drawString(58, body_y, "Library Member ID ")

    reg_x = 58 + c.stringWidth("Library Member ID ", "Helvetica", 14)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(SRM_BLUE)
    c.drawString(reg_x, body_y, reg_no)
    reg_w = c.stringWidth(reg_no, "Helvetica-Bold", 14)
    c.setStrokeColor(SRM_BLUE)
    c.setLineWidth(1)
    c.line(reg_x, body_y - 3, reg_x + reg_w, body_y - 3)

    role_x = reg_x + reg_w + 24
    c.setFont("Helvetica", 14)
    c.setFillColor(TEXT_BLACK)
    c.drawString(role_x, body_y, f"{role_label} of ")

    dept_x = role_x + c.stringWidth(f"{role_label} of ", "Helvetica", 14)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(SRM_BLUE)
    c.drawString(dept_x, body_y, dept_str)
    dept_w = c.stringWidth(dept_str, "Helvetica-Bold", 14)
    c.line(dept_x, body_y - 3, dept_x + dept_w, body_y - 3)

    dept_end_x = dept_x + dept_w + 8
    c.setFont("Helvetica", 14)
    c.setFillColor(TEXT_BLACK)
    c.drawString(dept_end_x, body_y, "Department")

    # Line 3: has returned all the books and non-books borrowed from the Library. He/she owes
    body_y -= line_spacing
    c.setFont("Helvetica", 14)
    c.setFillColor(TEXT_BLACK)
    c.drawString(58, body_y, "has returned all the books and non-books borrowed from the Library. He/she owes")

    # Line 4: no due to the Library.
    body_y -= 26
    c.drawString(58, body_y, "no due to the Library.")

    # 5. Date
    c.setFont("Helvetica", 13.5)
    c.drawString(58, 140, "Date: ")
    c.setFont("Helvetica-Bold", 13.5)
    c.drawString(100, 140, cert_date)

    # 6. Verification QR Code & Official Clearance Seal
    qr_img = qrcode.make(f"https://eeelibrary.org/my-books?q={reg_no}")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_reportlab = canvas.ImageReader(qr_buf)
    c.drawImage(qr_reportlab, 58, 48, width=70, height=70)

    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED_GRAY)
    c.drawString(136, 92, "Online Verified Clearance")
    c.drawString(136, 80, "Scan QR to confirm catalog record")
    c.drawString(136, 68, f"Ref: {cert_id}")

    # Official Green Badge Stamp
    badge_x = (w / 2) - 30
    c.setFillColor(colors.HexColor("#ECFDF5"))
    c.setStrokeColor(SUCCESS_GREEN)
    c.roundRect(badge_x - 70, 75, 160, 48, 8, fill=1, stroke=1)
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(SUCCESS_GREEN)
    c.drawCentredString(badge_x + 10, 104, "✓ NO DUE CLEARED")
    c.setFont("Helvetica", 8)
    c.setFillColor(SUCCESS_GREEN)
    c.drawCentredString(badge_x + 10, 88, "Zero Outstanding Records")

    # 7. In-Charges Signatures & Signatory Block
    # Signature image provided by user
    sig_path = os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "static", "images", "incharge_signature.png")
    sig_x = w - 240
    if os.path.exists(sig_path):
        c.drawImage(sig_path, sig_x + 20, 115, width=115, height=80, mask="auto")

    # Signatory details
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(TEXT_BLACK)
    c.drawRightString(w - 58, 110, "Dr. K. Saravanan")

    c.setFont("Helvetica", 9.5)
    c.setFillColor(MUTED_GRAY)
    c.drawRightString(w - 58, 96, "Associate Professor & Library In-Charge")
    c.drawRightString(w - 58, 83, "Department of Electrical and Electronics Engineering")
    c.drawRightString(w - 58, 70, "SRM Institute of Science and Technology")

    # Additional In-Charge mention
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawRightString(w - 58, 55, "Ms. Gomathy Lakshmi K, Teaching Assistant (Library In-Charge)")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()

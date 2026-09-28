"""
Email reminder and barcode delivery utility — sends barcodes, due dates, and overdue notices
"""

import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime


def send_email(to_addr: str, subject: str, body_html: str,
               smtp_host: str, smtp_port: int,
               smtp_user: str, smtp_password: str,
               from_addr: str = None,
               inline_images: dict = None) -> tuple[bool, str]:
    """Send a single email. Returns (success, error_message).
    inline_images: optional dict mapping content_id string to (image_bytes, subtype_str)
    """
    if not to_addr or not smtp_user or not smtp_password:
        return False, "Email configuration incomplete (SMTP user or password missing)"

    from_addr = from_addr or smtp_user

    if inline_images:
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = f"SRM EEE Library <{from_addr}>"
        msg["To"] = to_addr

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body_html, "html"))
        msg.attach(alt_part)

        for cid, (img_bytes, subtype) in inline_images.items():
            img_part = MIMEImage(img_bytes, _subtype=subtype)
            img_part.add_header("Content-ID", f"<{cid}>")
            img_part.add_header("Content-Disposition", "inline", filename=f"{cid}.{subtype}")
            msg.attach(img_part)
    else:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SRM EEE Library <{from_addr}>"
        msg["To"] = to_addr
        msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def build_patron_barcode_email(patron: dict, library_name: str = "SRM EEE Department Library", use_cid: bool = True) -> str:
    """Build an elegant Digital Library ID Card email with embedded barcode."""
    name = patron.get("name", "Student / Faculty")
    reg = patron.get("register_number", "")
    barcode_str = patron.get("barcode", "")
    ptype = (patron.get("patron_type", "") or "student").title()
    year = patron.get("year", "")
    section = patron.get("section", "")

    # 2D QR Code + 1D Barcode image tags
    qr_img_tag = ""
    barcode_img_tag = ""
    if use_cid:
        qr_img_tag = f'<img src="cid:qr_img" alt="QR {barcode_str}" style="width:170px; height:170px; display:block; margin:0 auto;" />'
        barcode_img_tag = f'<img src="cid:barcode_img" alt="{barcode_str}" style="max-width:250px; width:100%; height:auto; display:block; margin:0 auto;" />'
    else:
        try:
            from library_app.utils.barcode_utils import generate_barcode_image, generate_qr_image
            q_bytes = generate_qr_image(barcode_str)
            b_bytes = generate_barcode_image(barcode_str)
            q_b64 = base64.b64encode(q_bytes).decode("ascii")
            b_b64 = base64.b64encode(b_bytes).decode("ascii")
            qr_img_tag = f'<img src="data:image/png;base64,{q_b64}" alt="QR {barcode_str}" style="width:170px; height:170px; display:block; margin:0 auto;" />'
            barcode_img_tag = f'<img src="data:image/png;base64,{b_b64}" alt="{barcode_str}" style="max-width:250px; width:100%; height:auto; display:block; margin:0 auto;" />'
        except Exception:
            barcode_img_tag = f'<div style="font-family:monospace; font-size:24px; font-weight:bold; letter-spacing:4px; padding:10px;">{barcode_str}</div>'

    class_info = f"Class: Year {year} • Section {section}" if year else f"Role: {ptype}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:20px; background-color:#F4F6F1; font-family:'Segoe UI',Helvetica,Arial,sans-serif; color:#17241A;">
      <div style="max-width:540px; margin:0 auto; background:#FFFFFF; border:1px solid #DDE5D8; border-radius:20px; overflow:hidden; box-shadow:0 8px 24px rgba(0,0,0,0.06);">
        
        <!-- Header -->
        <div style="background:#1C3022; color:#FFFFFF; padding:26px 30px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#A7BFA0; font-weight:600; margin-bottom:4px;">
            Department of Electrical & Electronics Engineering
          </div>
          <h1 style="margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">
            SRM Institute of Science & Technology
          </h1>
          <div style="font-size:13px; color:#E3EBE1; margin-top:4px;">
            {library_name} • Digital Library Card
          </div>
        </div>

        <!-- Body / ID Card -->
        <div style="padding:28px 24px; text-align:center;">
          <p style="font-size:14.5px; color:#435A48; margin-top:0; margin-bottom:16px;">
            Hello <strong>{name}</strong>, here is your official digital library card. You can present this QR code on your phone screen at the desk to borrow or return books:
          </p>

          <!-- Digital Card Box -->
          <div style="background:#F8FAF6; border:2px dashed #CBD5E1; border-radius:18px; padding:22px 18px; margin:16px 0; text-align:center;">
            <div style="font-size:12px; font-weight:700; color:#1C3022; text-transform:uppercase; letter-spacing:0.8px;">
              SRM EEE DIGITAL LIBRARY CARD
            </div>
            
            <div style="font-size:18px; font-weight:700; color:#17241A; margin:8px 0 2px;">
              {name}
            </div>
            <div style="font-size:13px; color:#627265; margin-bottom:16px;">
              <strong>ID: {reg}</strong> • {class_info}
            </div>

            <!-- 2D QR Code Container (High Contrast for Phone Screens) -->
            <div style="background:#FFFFFF; border:2px solid #E2E8F0; border-radius:14px; padding:16px; display:inline-block; margin-bottom:12px; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
              {qr_img_tag}
              <div style="font-family:monospace; font-size:14px; font-weight:700; color:#0F172A; letter-spacing:2px; margin-top:8px;">
                {barcode_str}
              </div>
            </div>

            <!-- 1D Linear Barcode fallback -->
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:10px 8px; max-width:280px; margin:0 auto;">
              {barcode_img_tag}
            </div>

            <div style="margin-top:12px; font-size:11.5px; color:#166534; font-weight:600;">
              💡 Tip: Turn phone brightness to 100% when scanning at the desk
            </div>
          </div>

          <!-- Instructions -->
          <div style="text-align:left; background:#EBF2E9; border-radius:12px; padding:16px 18px; margin-top:18px; font-size:12.5px; color:#26432D; line-height:1.6;">
            <strong>📱 Fast Scanning Instructions:</strong>
            <ul style="margin:6px 0 0; padding-left:20px;">
              <li>Open this email or save this digital card to your phone photos.</li>
              <li>When borrowing or returning books, show the <strong>QR code</strong> to the librarian scanner.</li>
              <li>Hold your screen approx. 4 to 6 inches in front of the scanner.</li>
              <li>You can also browse catalog and check borrowed books at <a href="https://eeelibrary.org" style="color:#26432D; font-weight:bold;">eeelibrary.org</a>.</li>
          </div>
        </div>

        <!-- Footer -->
        <div style="background:#F8FAF6; border-top:1px solid #E5EBE1; padding:16px 20px; text-align:center; font-size:11.5px; color:#8A9A8D;">
          {library_name} • SRMIST Kattankulathur • <a href="https://eeelibrary.org" style="color:#8A9A8D; text-decoration:underline;">eeelibrary.org</a><br>
          This is an official library notification. Please keep your barcode safe.
        </div>
      </div>
    </body>
    </html>
    """


def send_patron_barcode_email(patron: dict, smtp_host: str, smtp_port: int,
                              smtp_user: str, smtp_password: str,
                              from_addr: str = None,
                              library_name: str = "SRM EEE Department Library") -> tuple[bool, str]:
    """Helper to generate and send an official digital barcode card to a patron's email."""
    email = (patron.get("email") or "").strip()
    if not email:
        return False, f"Patron {patron.get('name', 'patron')} does not have an email address"

    barcode_str = patron.get("barcode", "")
    inline_images = {}
    use_cid = False
    try:
        from library_app.utils.barcode_utils import generate_barcode_image, generate_qr_image
        img_bytes = generate_barcode_image(barcode_str)
        qr_bytes = generate_qr_image(barcode_str)
        inline_images["barcode_img"] = (img_bytes, "png")
        inline_images["qr_img"] = (qr_bytes, "png")
        use_cid = True
    except Exception:
        use_cid = False

    body_html = build_patron_barcode_email(patron, library_name=library_name, use_cid=use_cid)
    subject = f"[{library_name}] Official Digital Library Card — {patron.get('name')}"

    return send_email(
        to_addr=email,
        subject=subject,
        body_html=body_html,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_addr=from_addr,
        inline_images=inline_images if use_cid else None
    )


def build_due_reminder_email(patron_name: str, books: list[dict], library_name: str) -> str:
    """Build HTML email for due date reminder."""
    rows = ""
    for b in books:
        rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">{b.get('book_title','')}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;color:#e67e22;font-weight:600;">{b.get('due_date','')}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:'Segoe UI',Arial,sans-serif;color:#333;max-width:580px;margin:auto;padding:20px;">
    <div style="background:#1C3022;color:white;padding:20px;border-radius:12px 12px 0 0;text-align:center;">
        <h2 style="margin:0;">📚 {library_name}</h2>
        <p style="margin:5px 0 0;color:#A7BFA0;">Book Return Due Date Reminder</p>
    </div>
    <div style="padding:24px;background:#f9f9f9;border:1px solid #eee;border-radius:0 0 12px 12px;">
        <p>Dear <strong>{patron_name}</strong>,</p>
        <p>This is a reminder that the following textbook(s) borrowed from the department library are due soon:</p>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <thead>
                <tr style="background:#1C3022;color:white;font-size:12px;">
                    <th style="padding:10px;text-align:left;">Book Title</th>
                    <th style="padding:10px;text-align:left;">Due Date</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="margin-top:20px;font-size:13px;color:#555;">Please return or renew on time to avoid late fines of ₹2.00/day.</p>
        <p style="color:#888;font-size:11px;margin-top:24px;">Automated notice from {library_name}.</p>
    </div>
    </body></html>
    """


def build_overdue_email(patron_name: str, books: list[dict],
                        fine_per_day: float, library_name: str) -> str:
    """Build HTML email for overdue notice."""
    rows = ""
    today = datetime.now()
    total_fine = 0
    for b in books:
        try:
            due = datetime.strptime(b.get("due_date", ""), "%Y-%m-%d")
            days_overdue = (today - due).days
            fine = days_overdue * fine_per_day
            total_fine += fine
        except Exception:
            days_overdue = 0
            fine = 0
        rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">{b.get('book_title','')}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;color:#c0392b;">{b.get('due_date','')}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;color:#c0392b;font-weight:600;">{days_overdue} days</td>
            <td style="padding:10px;border-bottom:1px solid #eee;color:#c0392b;font-weight:700;">₹{fine:.2f}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:'Segoe UI',Arial,sans-serif;color:#333;max-width:580px;margin:auto;padding:20px;">
    <div style="background:#991B1B;color:white;padding:20px;border-radius:12px 12px 0 0;text-align:center;">
        <h2 style="margin:0;">📚 {library_name}</h2>
        <p style="margin:5px 0 0;color:#FECACA;">⚠️ Overdue Textbook Notice</p>
    </div>
    <div style="padding:24px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:0 0 12px 12px;">
        <p>Dear <strong>{patron_name}</strong>,</p>
        <p>The following textbook(s) borrowed under your account are <strong>overdue</strong> and accruing daily late fines:</p>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;">
            <thead>
                <tr style="background:#991B1B;color:white;font-size:12px;">
                    <th style="padding:10px;text-align:left;">Book Title</th>
                    <th style="padding:10px;text-align:left;">Due Date</th>
                    <th style="padding:10px;text-align:left;">Overdue</th>
                    <th style="padding:10px;text-align:left;">Fine</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <div style="margin-top:16px;font-size:14px;font-weight:700;color:#991B1B;">
            Total Pending Late Fine: ₹{total_fine:.2f}
        </div>
        <p style="margin-top:16px;color:#7F1D1D;font-size:13px;"><strong>Please return the textbook(s) to the department library immediately.</strong></p>
        <p style="color:#888;font-size:11px;margin-top:24px;">Automated notice from {library_name}.</p>
    </div>
    </body></html>
    """

"""
Email reminder and barcode delivery utility — sends barcodes, due dates, and overdue notices
"""

import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime


import socket

class IPv4SMTP(smtplib.SMTP):
    """SMTP client that forces IPv4 connections to prevent [Errno 101] Network is unreachable on Render/cloud hosts."""
    def _get_socket(self, host, port, timeout):
        err = None
        for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                if timeout is not None:
                    sock.settimeout(timeout)
                sock.connect(sa)
                return sock
            except socket.error as e:
                err = e
                if sock is not None:
                    sock.close()
        if err is not None:
            raise err
        raise socket.error(f"Could not resolve IPv4 address for {host}")


class IPv4SMTP_SSL(smtplib.SMTP_SSL):
    """SMTP_SSL client that forces IPv4 connections for port 465."""
    def _get_socket(self, host, port, timeout):
        err = None
        for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                if timeout is not None:
                    sock.settimeout(timeout)
                sock.connect(sa)
                new_sock = self.context.wrap_socket(sock, server_hostname=self._host)
                return new_sock
            except socket.error as e:
                err = e
                if sock is not None:
                    sock.close()
        if err is not None:
            raise err
        raise socket.error(f"Could not resolve IPv4 address for {host}")


import urllib.request
import urllib.error
import json
import os

def send_email_brevo(api_key: str, to_addr: str, subject: str, body_html: str,
                     sender_email: str = None,
                     sender_name: str = "SRM EEE Department Library",
                     reply_to: str = None,
                     to_name: str = None,
                     inline_images: dict = None,
                     attachments: list = None) -> tuple[bool, str]:
    """Send an email via Brevo's v3 HTTP REST API over Port 443 (HTTPS).
    Works on Render Free tier without outbound SMTP port blocking!
    """
    if not api_key or not api_key.strip():
        return False, "Brevo API key missing"
    if not to_addr or not to_addr.strip():
        return False, "Recipient email missing"

    # Default to verified sender if not specified
    if not sender_email or not sender_email.strip():
        try:
            from library_app.database import get_setting
            sender_email = get_setting("brevo_sender_email", "") or "saaqibheroindia@gmail.com"
        except Exception:
            sender_email = "saaqibheroindia@gmail.com"

    if not reply_to or not reply_to.strip():
        try:
            from library_app.database import get_setting
            reply_to = get_setting("email_reply_to", "") or get_setting("email_from", "") or "srmeeelibraray@gmail.com"
        except Exception:
            reply_to = "srmeeelibraray@gmail.com"

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "sender": {
            "name": sender_name or "SRM EEE Department Library",
            "email": sender_email.strip()
        },
        "to": [
            {
                "email": to_addr.strip(),
                "name": to_name or to_addr.strip()
            }
        ],
        "subject": subject,
        "htmlContent": body_html
    }

    if reply_to and reply_to.strip():
        payload["replyTo"] = {
            "name": sender_name or "SRM EEE Department Library",
            "email": reply_to.strip()
        }

    att_payload = []
    if inline_images:
        for cid, (img_bytes, subtype) in inline_images.items():
            att_payload.append({
                "content": base64.b64encode(img_bytes).decode("ascii"),
                "name": f"{cid}.{subtype}"
            })
    if attachments:
        for att in attachments:
            att_payload.append({
                "content": base64.b64encode(att["content"]).decode("ascii"),
                "name": att["filename"]
            })
    if att_payload:
        payload["attachment"] = att_payload

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return True, ""
    except urllib.error.HTTPError as e:
        err_text = e.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(err_text)
            msg = err_json.get("message") or err_text
        except Exception:
            msg = err_text
        if e.code == 401 or "unauthorized" in msg.lower() or "key not found" in msg.lower():
            return False, "Brevo Authentication Failed: Invalid Brevo API key. Please check your key at app.brevo.com/settings/keys/api"
        return False, f"Brevo HTTP {e.code}: {msg}"
    except Exception as e:
        return False, f"Brevo API error: {e}"


def send_email(to_addr: str, subject: str, body_html: str,
               smtp_host: str = "smtp.gmail.com", smtp_port: int = 465,
               smtp_user: str = "", smtp_password: str = "",
               from_addr: str = None,
               inline_images: dict = None,
               brevo_api_key: str = None,
               attachments: list = None) -> tuple[bool, str]:
    """Send an email using Brevo HTTP API (if configured) or fallback to direct SMTP."""
    if not brevo_api_key:
        try:
            from library_app.database import get_setting
            brevo_api_key = get_setting("brevo_api_key", "")
        except Exception:
            brevo_api_key = os.environ.get("BREVO_API_KEY", "")

    if brevo_api_key and str(brevo_api_key).strip():
        sender_email = None
        reply_to = None
        lib_name = "SRM EEE Department Library"
        try:
            from library_app.database import get_setting
            sender_email = get_setting("brevo_sender_email", "")
            reply_to = get_setting("email_reply_to", "")
            lib_name = get_setting("library_name", "SRM EEE Department Library")
        except Exception:
            pass

        if not sender_email or not sender_email.strip():
            sender_email = "saaqibheroindia@gmail.com"

        return send_email_brevo(
            api_key=str(brevo_api_key).strip(),
            to_addr=to_addr,
            subject=subject,
            body_html=body_html,
            sender_email=sender_email,
            sender_name=lib_name,
            reply_to=reply_to,
            inline_images=inline_images,
            attachments=attachments
        )

    if not to_addr or not smtp_user or not smtp_password:
        return False, "Email configuration incomplete (SMTP user/password or Brevo API key missing)"

    from_addr = from_addr or smtp_user

    if attachments:
        from email.mime.application import MIMEApplication
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"SRM EEE Library <{from_addr}>"
        msg["To"] = to_addr

        if inline_images:
            related_part = MIMEMultipart("related")
            alt_part = MIMEMultipart("alternative")
            alt_part.attach(MIMEText(body_html, "html"))
            related_part.attach(alt_part)
            for cid, (img_bytes, subtype) in inline_images.items():
                img_part = MIMEImage(img_bytes, _subtype=subtype)
                img_part.add_header("Content-ID", f"<{cid}>")
                img_part.add_header("Content-Disposition", "inline", filename=f"{cid}.{subtype}")
                related_part.attach(img_part)
            msg.attach(related_part)
        else:
            msg.attach(MIMEText(body_html, "html"))

        for att in attachments:
            part = MIMEApplication(att["content"], Name=att["filename"])
            part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
            msg.attach(part)
    elif inline_images:
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

    def _try_connect(port):
        if port == 465 or "gmail" in smtp_host.lower():
            s = IPv4SMTP_SSL(smtp_host, 465, timeout=12)
            s.ehlo("localhost")
        else:
            s = IPv4SMTP(smtp_host, port, timeout=10)
            s.ehlo("localhost")
            s.starttls()
            s.ehlo("localhost")
        return s

    current_step = "initialization"
    server = None
    try:
        clean_user = smtp_user.strip()
        clean_pass = smtp_password.strip().replace(" ", "")

        # For Gmail on cloud hosting (Render), port 465 SSL is direct, fast and never blocked
        if "gmail" in smtp_host.lower():
            ports_to_try = [465]
        else:
            ports_to_try = [smtp_port] if smtp_port == 465 else [smtp_port, 465]

        current_step = f"connecting to {smtp_host}"
        last_conn_err = None
        for p in ports_to_try:
            try:
                server = _try_connect(p)
                break
            except Exception as ce:
                last_conn_err = ce
                if server:
                    try: server.close()
                    except Exception: pass
                server = None

        if not server:
            raise last_conn_err or Exception(f"Could not connect to {smtp_host} on ports {ports_to_try}")

        current_step = f"authenticating with {clean_user}"
        server.login(clean_user, clean_pass)

        current_step = f"dispatching email to {to_addr}"
        server.sendmail(from_addr, [to_addr], msg.as_string())

        current_step = "closing connection"
        server.quit()
        return True, ""
    except smtplib.SMTPAuthenticationError as e:
        err_msg = str(e)
        if "5.7.8" in err_msg or "Username and Password not accepted" in err_msg or "Application-specific password" in err_msg or "BadCredentials" in err_msg:
            return False, "Google SMTP Login Failed: Google requires a 16-character App Password (not your standard Gmail password). Make sure 2-Step Verification is ON, then generate an App Password at https://myaccount.google.com/apppasswords"
        return False, f"SMTP Authentication Error: {err_msg}"
    except smtplib.SMTPConnectError as e:
        return False, f"Could not connect to SMTP host {smtp_host} — {e}"
    except Exception as e:
        return False, f"Delivery error during {current_step}: {e}"
    finally:
        if server:
            try:
                server.close()
            except Exception:
                pass


def build_patron_barcode_email(patron: dict, library_name: str = "SRM EEE Department Library", use_cid: bool = True) -> str:
    """Build an elegant Digital Library ID Card email with embedded barcode."""
    name = patron.get("name", "Student / Faculty")
    reg = patron.get("register_number", "")
    barcode_str = patron.get("barcode", "")
    ptype = (patron.get("patron_type", "") or "student").title()
    year = patron.get("year", "")
    section = patron.get("section", "")

    # 1D Linear Barcode image tag — uses public hosted URL so email clients (Gmail, Outlook, Apple Mail) render barcode lines
    barcode_url = f"https://eeelibrary.org/api/barcode/image/{barcode_str}"
    barcode_img_tag = f'<img src="{barcode_url}" alt="Barcode {barcode_str}" width="280" style="width:280px; max-width:100%; height:auto; display:block; margin:0 auto; border:none;" />'

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
            Hello <strong>{name}</strong>, here is your official digital library card. You can present this barcode on your phone screen at the desk to borrow or return books:
          </p>

          <!-- Digital Card Box -->
          <div style="background:#F8FAF6; border:2px dashed #CBD5E1; border-radius:18px; padding:24px 20px; margin:16px 0; text-align:center;">
            <div style="font-size:12px; font-weight:700; color:#1C3022; text-transform:uppercase; letter-spacing:0.8px;">
              SRM EEE DIGITAL LIBRARY CARD
            </div>
            
            <div style="font-size:19px; font-weight:700; color:#17241A; margin:8px 0 2px;">
              {name}
            </div>
            <div style="font-size:13px; color:#627265; margin-bottom:18px;">
              <strong>ID: {reg}</strong> • {class_info}
            </div>

            <!-- 1D Linear Barcode Container -->
            <div style="background:#FFFFFF; border:2px solid #E2E8F0; border-radius:14px; padding:18px 16px; max-width:340px; margin:0 auto; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
              {barcode_img_tag}
              <div style="font-family:'Consolas',monospace; font-size:17px; font-weight:700; color:#0F172A; letter-spacing:3px; margin-top:8px;">
                {barcode_str}
              </div>
            </div>

            <div style="margin-top:14px; font-size:11.5px; color:#166534; font-weight:600;">
              Tip: Turn phone brightness to 100% when presenting to the desk scanner
            </div>
          </div>

          <!-- Instructions -->
          <div style="text-align:left; background:#EBF2E9; border-radius:12px; padding:16px 18px; margin-top:18px; font-size:12.5px; color:#26432D; line-height:1.6;">
            <strong>Fast Scanning Instructions:</strong>
            <ul style="margin:6px 0 0; padding-left:20px;">
              <li>Open this email or save this digital card image to your phone gallery.</li>
              <li>When borrowing or returning books, show your <strong>barcode</strong> to the librarian scanner.</li>
              <li>Hold your screen approx. 4 to 6 inches in front of the scanner lens.</li>
              <li>You can also browse the catalog and check borrowed books at <a href="https://eeelibrary.org" style="color:#26432D; font-weight:bold;">eeelibrary.org</a>.</li>
            </ul>
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


def send_patron_barcode_email(patron: dict, smtp_host: str = "smtp.gmail.com", smtp_port: int = 465,
                              smtp_user: str = "", smtp_password: str = "",
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
        from library_app.utils.barcode_utils import generate_barcode_image
        img_bytes = generate_barcode_image(barcode_str)
        inline_images["barcode_img"] = (img_bytes, "png")
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
        <h2 style="margin:0;">{library_name}</h2>
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
        <h2 style="margin:0;">{library_name}</h2>
        <p style="margin:5px 0 0;color:#FECACA;">Overdue Textbook Notice</p>
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


def send_no_due_certificate_email(patron: dict, cert_pdf_bytes: bytes, cert_id: str, to_email: str = None) -> tuple[bool, str]:
    """
    Sends the official No Due Clearance Certificate to the patron via email with PDF attached.
    """
    target_email = (to_email or patron.get("email") or patron.get("parent_email") or "").strip()
    if not target_email:
        return False, "Recipient email address is missing."

    name = patron.get("name", "Student / Faculty")
    reg = patron.get("register_number") or patron.get("barcode") or "—"
    date_str = datetime.now().strftime("%d %B %Y")

    subject = f"Official No Due Certificate — SRM EEE Department Library [{reg}]"

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:20px; background-color:#F4F6F1; font-family:'Segoe UI',Helvetica,Arial,sans-serif; color:#17241A;">
      <div style="max-width:560px; margin:0 auto; background:#FFFFFF; border:1px solid #DDE5D8; border-radius:20px; overflow:hidden; box-shadow:0 8px 24px rgba(0,0,0,0.06);">
        
        <!-- Header -->
        <div style="background:#1C3022; color:#FFFFFF; padding:26px 30px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#A7BFA0; font-weight:600; margin-bottom:4px;">
            SRM Institute of Science and Technology • EEE Department
          </div>
          <h1 style="margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">
            Official Library Clearance
          </h1>
          <p style="margin:6px 0 0; font-size:13px; color:#DDE5D8;">No Due Certificate Issued</p>
        </div>

        <!-- Content -->
        <div style="padding:28px 30px;">
          <p style="font-size:15px; margin:0 0 16px; line-height:1.6;">
            Dear <strong>{name}</strong>,
          </p>
          <p style="font-size:14px; margin:0 0 18px; line-height:1.6; color:#374151;">
            We are pleased to inform you that your library account with the <strong>SRM EEE Department Library</strong> has been verified. 
            All borrowed books, journals, and materials have been returned with <strong>zero pending dues</strong>.
          </p>

          <!-- Clearance Box -->
          <div style="background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:14px; padding:18px 20px; margin-bottom:22px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
              <span style="display:inline-block; width:10px; height:10px; background:#16A34A; border-radius:50%;"></span>
              <strong style="color:#166534; font-size:14.5px;">Clearance Status: Cleared / No Due</strong>
            </div>
            <table style="width:100%; font-size:12.5px; border-collapse:collapse; color:#1F2937;">
              <tr>
                <td style="padding:4px 0; color:#6B7280; width:40%;">Register Number / ID:</td>
                <td style="padding:4px 0; font-weight:600;">{reg}</td>
              </tr>
              <tr>
                <td style="padding:4px 0; color:#6B7280;">Certificate Ref:</td>
                <td style="padding:4px 0; font-weight:600;">{cert_id}</td>
              </tr>
              <tr>
                <td style="padding:4px 0; color:#6B7280;">Date of Clearance:</td>
                <td style="padding:4px 0; font-weight:600;">{date_str}</td>
              </tr>
              <tr>
                <td style="padding:4px 0; color:#6B7280;">Outstanding Dues:</td>
                <td style="padding:4px 0; font-weight:700; color:#166534;">₹0.00 (Nil)</td>
              </tr>
            </table>
          </div>

          <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:14px 18px; margin-bottom:22px; font-size:13px; color:#475569; line-height:1.5;">
            📎 <strong>Official PDF Attached:</strong> Your signed and seal-verified No Due Certificate has been attached to this email as a PDF document. You can download and submit it for graduation, exam clearance, or transfer requirements.
          </div>

          <div style="border-top:1px solid #E5E7EB; padding-top:18px; margin-top:20px;">
            <p style="margin:0 0 4px; font-size:12px; font-weight:700; color:#111827;">Library In-Charges:</p>
            <p style="margin:0; font-size:12px; color:#4B5563; line-height:1.5;">
              <strong>Dr. K. Saravanan</strong>, Associate Professor &amp; Library In-Charge<br>
              <strong>Ms. Gomathy Lakshmi K</strong>, Teaching Assistant &amp; Library In-Charge<br>
              Department of Electrical &amp; Electronics Engineering<br>
              SRM Institute of Science and Technology
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div style="background:#F4F6F1; padding:14px 20px; text-align:center; font-size:11px; color:#6B7280; border-top:1px solid #DDE5D8;">
          SRM EEE Department Library • Official Clearance Portal • <a href="https://eeelibrary.org" style="color:#1C3022; font-weight:600; text-decoration:none;">eeelibrary.org</a>
        </div>
      </div>
    </body>
    </html>
    """

    filename = f"No_Due_Certificate_{reg}.pdf"
    attachments = [{
        "filename": filename,
        "content": cert_pdf_bytes,
        "mime_type": "application/pdf"
    }]

    return send_email(
        to_addr=target_email,
        subject=subject,
        body_html=body_html,
        attachments=attachments
    )


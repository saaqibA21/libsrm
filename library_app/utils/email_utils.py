"""
Email reminder utility — sends due date and overdue notifications
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_email(to_addr: str, subject: str, body_html: str,
               smtp_host: str, smtp_port: int,
               smtp_user: str, smtp_password: str,
               from_addr: str = None) -> tuple[bool, str]:
    """Send a single email. Returns (success, error_message)."""
    if not to_addr or not smtp_user or not smtp_password:
        return False, "Email configuration incomplete"

    from_addr = from_addr or smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"SRM Library <{from_addr}>"
    msg["To"] = to_addr

    part = MIMEText(body_html, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def build_due_reminder_email(patron_name: str, books: list[dict], library_name: str) -> str:
    """Build HTML email for due date reminder."""
    rows = ""
    for b in books:
        rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{b.get('book_title','')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#e67e22;">{b.get('due_date','')}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;">
    <div style="background:#1565C0;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0;">📚 {library_name}</h2>
        <p style="margin:5px 0 0;">Book Return Reminder</p>
    </div>
    <div style="padding:20px;background:#f9f9f9;">
        <p>Dear <strong>{patron_name}</strong>,</p>
        <p>This is a friendly reminder that the following book(s) are due for return soon:</p>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:6px;overflow:hidden;">
            <thead>
                <tr style="background:#1565C0;color:white;">
                    <th style="padding:10px;text-align:left;">Book Title</th>
                    <th style="padding:10px;text-align:left;">Due Date</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="margin-top:20px;">Please return the book(s) on time to avoid late fines.</p>
        <p style="color:#888;font-size:12px;">This is an automated message from {library_name}. Please do not reply.</p>
    </div>
    </body></html>
    """


def build_overdue_email(patron_name: str, books: list[dict],
                        fine_per_day: float, library_name: str) -> str:
    """Build HTML email for overdue notice."""
    rows = ""
    today = datetime.now()
    for b in books:
        try:
            due = datetime.strptime(b.get("due_date", ""), "%Y-%m-%d")
            days_overdue = (today - due).days
            fine = days_overdue * fine_per_day
        except Exception:
            days_overdue = 0
            fine = 0
        rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{b.get('book_title','')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#c0392b;">{b.get('due_date','')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#c0392b;">{days_overdue} days</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#c0392b;">₹{fine:.2f}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto;">
    <div style="background:#c0392b;color:white;padding:20px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0;">📚 {library_name}</h2>
        <p style="margin:5px 0 0;">⚠️ Overdue Book Notice</p>
    </div>
    <div style="padding:20px;background:#fef9f9;">
        <p>Dear <strong>{patron_name}</strong>,</p>
        <p>The following book(s) are <strong>overdue</strong> and accruing fines:</p>
        <table style="width:100%;border-collapse:collapse;background:white;border-radius:6px;overflow:hidden;">
            <thead>
                <tr style="background:#c0392b;color:white;">
                    <th style="padding:10px;text-align:left;">Book Title</th>
                    <th style="padding:10px;text-align:left;">Due Date</th>
                    <th style="padding:10px;text-align:left;">Days Overdue</th>
                    <th style="padding:10px;text-align:left;">Fine</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="margin-top:20px;color:#c0392b;"><strong>Please return the book(s) immediately to stop accruing fines.</strong></p>
        <p style="color:#888;font-size:12px;">This is an automated message from {library_name}. Please do not reply.</p>
    </div>
    </body></html>
    """

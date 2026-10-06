"""
Automated Daily Circulation & Analytics Report Service for SRM EEE Library
Generates and delivers daily activity PDF report to Dr. K. Saravanan (saravank3@srmist.edu.in).
"""

import os
from datetime import datetime, timezone, timedelta
from library_app.database import (
    get_setting, set_setting, get_dashboard_stats,
    get_today_transactions, get_overdue_transactions
)
from library_app.utils.report_pdf import generate_circulation_report_pdf
from library_app.utils.email_utils import send_email

# Indian Standard Time (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_RECIPIENT = "saravank3@srmist.edu.in, srmktreeedeptlibrary@gmail.com"


def get_ist_now():
    """Get current datetime in Indian Standard Time."""
    return datetime.now(IST)


def get_daily_report_recipient() -> str:
    """Fetch designated recipient email for daily library reports."""
    recipient = get_setting("daily_report_recipient_email", "").strip()
    return recipient if recipient else DEFAULT_RECIPIENT


def send_daily_report_email(recipient: str = None, force: bool = False) -> tuple[bool, str]:
    """
    Generate the official daily circulation report PDF and email it to Dr. K. Saravanan.
    Returns (success: bool, message: str).
    """
    target_email = (recipient or "").strip() or get_daily_report_recipient()
    if not target_email:
        target_email = DEFAULT_RECIPIENT

    now_ist = get_ist_now()
    today_str = now_ist.strftime("%Y-%m-%d")
    date_display = now_ist.strftime("%d-%B-%Y")
    time_display = now_ist.strftime("%I:%M %p IST")

    # 1. Fetch live metrics
    stats = get_dashboard_stats()
    overdue_list = get_overdue_transactions()
    today_txns = get_today_transactions()

    issued_today = stats.get("issued_today", 0)
    returned_today = stats.get("returned_today", 0)
    active_loans = stats.get("issued_books", 0)
    overdue_count = len(overdue_list)
    total_catalog = stats.get("total_books", 0)
    available_books = stats.get("available_books", 0)
    pending_fines = float(stats.get("pending_fines", 0.0))

    # 2. Generate Circulation Report PDF
    try:
        pdf_bytes = generate_circulation_report_pdf()
        if not pdf_bytes or len(pdf_bytes) < 100:
            return False, "Failed to generate daily circulation report PDF"
    except Exception as e:
        return False, f"PDF generation error: {e}"

    # 3. Build HTML Email Body
    subject = f"SRM EEE Library — Automated Daily Circulation & Analytics Report ({date_display})"

    # Format today's transactions snippet
    if today_txns:
        tx_rows = ""
        for t in today_txns[:8]:
            st = (t.get("status") or "").title()
            st_color = "#16A34A" if st == "Returned" else "#D97706"
            tx_rows += f"""
            <tr style="border-bottom: 1px solid #E5E7EB;">
              <td style="padding: 6px 8px; font-weight: 600;">{t.get('book_title', '')[:35]}</td>
              <td style="padding: 6px 8px; color: #4B5563;">{t.get('patron_name', '')} ({t.get('patron_reg', '') or '—'})</td>
              <td style="padding: 6px 8px; color: {st_color}; font-weight: 700;">{st}</td>
            </tr>
            """
        today_activity_html = f"""
        <div style="margin-top: 18px; background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 14px 16px;">
          <div style="font-size: 13px; font-weight: 700; color: #1F2937; margin-bottom: 8px;">
            Today's Circulation Events ({len(today_txns)} transactions)
          </div>
          <table style="width: 100%; font-size: 11.5px; border-collapse: collapse; text-align: left;">
            <thead>
              <tr style="background: #F9FAFB; color: #6B7280; font-size: 10.5px; text-transform: uppercase;">
                <th style="padding: 6px 8px;">Book Title</th>
                <th style="padding: 6px 8px;">Borrower</th>
                <th style="padding: 6px 8px;">Action</th>
              </tr>
            </thead>
            <tbody>
              {tx_rows}
            </tbody>
          </table>
        </div>
        """
    else:
        today_activity_html = """
        <div style="margin-top: 14px; background: #F9FAFB; border: 1px dashed #D1D5DB; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #6B7280; text-align: center;">
          <i>No checkouts or returns were recorded today.</i>
        </div>
        """

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background:#F4F6F1; margin:0; padding:24px 12px; color:#1F2937;">
      <div style="max-width:660px; margin:0 auto; background:#FFFFFF; border:1px solid #D1D5DB; border-radius:16px; overflow:hidden; box-shadow:0 6px 24px rgba(0,0,0,0.06);">
        
        <!-- Header -->
        <div style="background:#1C3022; color:#FFFFFF; padding:26px 30px; text-align:center;">
          <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#A7BFA0; font-weight:600; margin-bottom:4px;">
            SRM Institute of Science and Technology • Kattankulathur
          </div>
          <h1 style="margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">
            Department of Electrical &amp; Electronics Engineering
          </h1>
          <p style="margin:6px 0 0; font-size:13.5px; color:#DDE5D8;">
            Library Circulation &amp; Operational Analytics Daily Report
          </p>
        </div>

        <!-- Body Content -->
        <div style="padding:28px 30px;">
          <p style="font-size:15px; margin:0 0 14px; line-height:1.6;">
            Respected <strong>Dr. K. Saravanan &amp; Library Team</strong>,
          </p>
          <p style="font-size:13.5px; margin:0 0 18px; line-height:1.6; color:#374151;">
            Here is your automated daily library activity, circulation statistics, and holdings status for <strong>{date_display}</strong> ({time_display}). 
            The full official report document is attached below as a printable PDF.
          </p>

          <!-- Key Stats Grid -->
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-bottom:18px;">
            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:12px; text-align:center;">
              <div style="font-size:10.5px; text-transform:uppercase; color:#166534; font-weight:700;">Issued Today</div>
              <div style="font-size:22px; font-weight:800; color:#166534; margin-top:2px;">{issued_today}</div>
            </div>
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:12px; text-align:center;">
              <div style="font-size:10.5px; text-transform:uppercase; color:#1E40AF; font-weight:700;">Returned Today</div>
              <div style="font-size:22px; font-weight:800; color:#1E40AF; margin-top:2px;">{returned_today}</div>
            </div>
            <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:10px; padding:12px; text-align:center;">
              <div style="font-size:10.5px; text-transform:uppercase; color:#991B1B; font-weight:700;">Overdue Books</div>
              <div style="font-size:22px; font-weight:800; color:#991B1B; margin-top:2px;">{overdue_count}</div>
            </div>
          </div>

          <!-- Summary Table -->
          <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:14px 18px; margin-bottom:18px;">
            <table style="width:100%; font-size:12.5px; border-collapse:collapse; color:#374151;">
              <tr>
                <td style="padding:5px 0; color:#6B7280; width:50%;">Currently Active Borrowed Books:</td>
                <td style="padding:5px 0; font-weight:700; color:#0F172A;">{active_loans} books</td>
              </tr>
              <tr>
                <td style="padding:5px 0; color:#6B7280;">Total Books in Catalog:</td>
                <td style="padding:5px 0; font-weight:700; color:#0F172A;">{total_catalog} books ({available_books} on shelf)</td>
              </tr>
              <tr>
                <td style="padding:5px 0; color:#6B7280;">Total Registered Members:</td>
                <td style="padding:5px 0; font-weight:700; color:#0F172A;">{stats.get('total_patrons', 0)} (Students &amp; Faculty)</td>
              </tr>
              <tr>
                <td style="padding:5px 0; color:#6B7280;">Pending Late Fines:</td>
                <td style="padding:5px 0; font-weight:700; color:#991B1B;">₹{pending_fines:.2f}</td>
              </tr>
            </table>
          </div>

          <!-- Activity Highlights -->
          {today_activity_html}

          <!-- PDF Attachment Notice -->
          <div style="background:#F0FDF4; border:1.5px solid #86EFAC; border-radius:12px; padding:14px 18px; margin-top:20px; font-size:13px; color:#14532D; line-height:1.5;">
            📎 <strong>Comprehensive PDF Attached:</strong> The complete circulation document <code>SRM_EEE_Library_Daily_Report_{today_str}.pdf</code> has been attached with full circulation history, borrower rankings, and overdue breakdown.
          </div>

          <!-- Signatures -->
          <div style="border-top:1px solid #E5E7EB; padding-top:18px; margin-top:24px;">
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
          SRM EEE Department Library Management System • <a href="https://eeelibrary.org" style="color:#1C3022; font-weight:600; text-decoration:none;">eeelibrary.org</a> • Feedback: <a href="mailto:saravank3@srmist.edu.in" style="color:#1C3022;">saravank3@srmist.edu.in</a>
        </div>
      </div>
    </body>
    </html>
    """

    filename = f"SRM_EEE_Library_Daily_Report_{today_str}.pdf"
    attachments = [{
        "filename": filename,
        "content": pdf_bytes,
        "mime_type": "application/pdf"
    }]

    # 4. Dispatch Email
    ok, err = send_email(
        to_addr=target_email,
        subject=subject,
        body_html=body_html,
        attachments=attachments
    )

    # 5. Record Dispatch Status in Database Settings
    status_label = "Success" if ok else f"Failed: {err}"
    set_setting("daily_report_last_status", status_label)
    set_setting("daily_report_last_sent_time", time_display)
    set_setting("daily_report_last_sent_date", today_str)
    set_setting("daily_report_last_recipient", target_email)

    if ok:
        msg = f"Daily circulation report successfully emailed to {target_email} with PDF attached ({len(pdf_bytes)} bytes)!"
        print(f"[Daily-Report] {msg}")
        return True, msg
    else:
        msg = f"Failed to deliver daily report to {target_email}: {err}"
        print(f"[Daily-Report] {msg}")
        return False, msg


def check_and_run_daily_report_email():
    """
    Called periodically by background scheduler (every 10 minutes).
    If local IST time is >= 18:00 (6:00 PM IST) and today's report hasn't been emailed yet,
    generates and emails the daily report to Dr. K. Saravanan.
    """
    now = get_ist_now()
    if now.hour >= 18:  # 6:00 PM IST or later
        today_str = now.strftime("%Y-%m-%d")
        last_date = get_setting("daily_report_last_sent_date", "")
        if last_date == today_str:
            return None, "Daily report already emailed today"

        # Record date immediately to prevent concurrent worker race conditions
        set_setting("daily_report_last_sent_date", today_str)
        recipient = get_daily_report_recipient()
        print(f"[Daily-Report] Local time is {now.strftime('%I:%M %p IST')}. Triggering scheduled 6:00 PM daily report email to {recipient}...")

        ok, msg = send_daily_report_email(recipient=recipient, force=False)
        return ok, msg

    return None, "Not yet 6:00 PM IST or already emailed today"

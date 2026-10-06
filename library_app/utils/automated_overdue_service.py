"""
Automated Daily Overdue Email Notice Service for SRM EEE Library
Scans circulation records for overdue books and delivers consolidated itemized notices
to borrowers.

SAFETY DESIGN:
- Default state is PAUSED (auto_overdue_email_active = "0") to prevent unintended emails
  while test/fake overdue records are in the database.
- Supports dry_run mode to preview recipient counts and fine breakdowns without sending.
- Admin can enable/disable auto-pilot anytime from Settings or via API.
"""

import os
from datetime import datetime, timezone, timedelta
from library_app.database import (
    get_setting, set_setting, get_connection,
    get_overdue_transactions
)
from library_app.utils.email_utils import send_email, build_overdue_email

# Indian Standard Time (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    """Current datetime in Indian Standard Time (UTC+5:30)."""
    return datetime.now(IST)


def is_auto_overdue_active() -> bool:
    """Check if the automated daily overdue dispatch is active."""
    return get_setting("auto_overdue_email_active", "0") == "1"


def get_auto_overdue_status() -> dict:
    """Return complete status and metrics for the automated overdue service."""
    active = is_auto_overdue_active()
    hour = int(get_setting("auto_overdue_email_hour", "9") or "9")
    last_run_date = get_setting("auto_overdue_last_run_date", "")
    last_run_time = get_setting("auto_overdue_last_run_time", "")
    last_sent_count = int(get_setting("auto_overdue_last_sent_count", "0") or "0")
    status_msg = get_setting("auto_overdue_last_status", "Paused (Safe Mode: Test/Fake Data)")

    now_ist = get_ist_now()
    today_str = now_ist.strftime("%Y-%m-%d")
    ran_today = (last_run_date == today_str)

    overdue_txns = get_overdue_transactions()
    total_overdue_books = len(overdue_txns)

    unique_patrons = set()
    patrons_with_email = set()
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    total_accrued_fine = 0.0

    today_dt = datetime.now()
    for txn in overdue_txns:
        pid = txn.get("patron_id")
        if pid:
            unique_patrons.add(pid)
            if txn.get("patron_email"):
                patrons_with_email.add(pid)
        try:
            due_dt = datetime.strptime(txn.get("due_date", ""), "%Y-%m-%d")
            days_over = max(0, (today_dt - due_dt).days)
            total_accrued_fine += days_over * fine_rate
        except Exception:
            pass

    if active:
        if ran_today:
            next_run_desc = f"Completed for today ({last_run_time}). Next run tomorrow at {hour}:00 AM IST."
        else:
            next_run_desc = f"Active — Scheduled for today at {hour}:00 AM IST."
    else:
        next_run_desc = "Paused (Safe Mode: Fake test data present). Toggle ON in Settings to activate."

    return {
        "active": active,
        "schedule_hour": hour,
        "last_run_date": last_run_date,
        "last_run_time": last_run_time,
        "last_sent_count": last_sent_count,
        "status_msg": status_msg,
        "total_overdue_books": total_overdue_books,
        "unique_overdue_patrons": len(unique_patrons),
        "patrons_with_email": len(patrons_with_email),
        "total_accrued_fine": round(total_accrued_fine, 2),
        "ran_today": ran_today,
        "next_run_desc": next_run_desc
    }


def record_overdue_dispatch(patron_id: int, email: str, books_count: int, total_fine: float, status: str, err: str = None):
    """Log an overdue notice dispatch record into database."""
    try:
        conn = get_connection()
        conn.execute("""
            INSERT INTO overdue_dispatches (patron_id, patron_email, books_count, total_fine, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (patron_id, email, books_count, total_fine, status, err))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Overdue-Service] Could not log dispatch: {e}")


def dispatch_overdue_emails(dry_run: bool = False, force: bool = False) -> tuple[bool, dict]:
    """
    Process all overdue transactions and deliver notices.
    If dry_run=True, simulates the run without dispatching any emails.
    If force=False and service is inactive, aborts safely.
    """
    active = is_auto_overdue_active()
    if not active and not force and not dry_run:
        msg = "Automated overdue emails are currently PAUSED (safe mode: fake test data). Turn ON in Settings to enable live dispatches."
        return False, {"message": msg, "sent": 0, "failed": 0, "active": False}

    overdue_txns = get_overdue_transactions()
    if not overdue_txns:
        return True, {"message": "No overdue books currently recorded in circulation.", "sent": 0, "failed": 0, "active": active}

    lib_name = get_setting("library_name", "SRM EEE Department Library")
    fine_rate = float(get_setting("fine_per_day", "2.0"))

    # Group overdue books by patron
    patron_groups = {}
    today_dt = datetime.now()
    for txn in overdue_txns:
        email = (txn.get("patron_email") or "").strip()
        if not email:
            continue
        pid = txn.get("patron_id") or email
        if pid not in patron_groups:
            patron_groups[pid] = {
                "patron_id": txn.get("patron_id"),
                "name": txn.get("patron_name", "Patron"),
                "email": email,
                "reg": txn.get("register_number", ""),
                "patron_type": txn.get("patron_type", "student"),
                "books": [],
                "total_fine": 0.0
            }
        
        try:
            due_dt = datetime.strptime(txn.get("due_date", ""), "%Y-%m-%d")
            days_over = max(0, (today_dt - due_dt).days)
            fine = days_over * fine_rate
        except Exception:
            days_over = 0
            fine = 0.0

        txn_copy = dict(txn)
        txn_copy["days_overdue"] = days_over
        txn_copy["calculated_fine"] = fine
        patron_groups[pid]["books"].append(txn_copy)
        patron_groups[pid]["total_fine"] += fine

    if not patron_groups:
        return True, {"message": "Overdue books found, but none of the borrowers have email addresses registered.", "sent": 0, "failed": 0}

    # Dry-Run Simulation Mode (Safe Preview)
    if dry_run:
        previews = []
        for pid, data in patron_groups.items():
            previews.append({
                "patron_name": data["name"],
                "email": data["email"],
                "register_number": data["reg"],
                "overdue_books_count": len(data["books"]),
                "books": [
                    {
                        "title": b.get("book_title", ""),
                        "due_date": b.get("due_date", ""),
                        "days_overdue": b.get("days_overdue", 0),
                        "fine": round(b.get("calculated_fine", 0.0), 2)
                    }
                    for b in data["books"]
                ],
                "total_fine": round(data["total_fine"], 2)
            })

        return True, {
            "dry_run": True,
            "message": f"Dry-run simulation successful: {len(previews)} patron(s) with {len(overdue_txns)} overdue book(s) identified. Zero emails were sent.",
            "eligible_patrons": len(previews),
            "total_overdue_books": len(overdue_txns),
            "previews": previews
        }

    # Live Dispatch Mode
    sent_count = 0
    failed_count = 0
    errors = []

    for pid, data in patron_groups.items():
        email = data["email"]
        name = data["name"]
        books = data["books"]
        total_fine = data["total_fine"]

        subject = f"[{lib_name}] Urgent: Overdue Textbook Circulation Notice ({len(books)} item{'s' if len(books) > 1 else ''})"
        body_html = build_overdue_email(name, books, fine_rate, lib_name, patron_info=data)

        ok, err = send_email(
            to_addr=email,
            subject=subject,
            body_html=body_html
        )

        status = "sent" if ok else "failed"
        record_overdue_dispatch(data["patron_id"] or 0, email, len(books), total_fine, status, err if not ok else None)

        if ok:
            sent_count += 1
        else:
            failed_count += 1
            errors.append(f"{name} ({email}): {err}")

    now_ist = get_ist_now()
    today_str = now_ist.strftime("%Y-%m-%d")
    time_str = now_ist.strftime("%I:%M %p IST")

    set_setting("auto_overdue_last_run_date", today_str)
    set_setting("auto_overdue_last_run_time", time_str)
    set_setting("auto_overdue_last_sent_count", str(sent_count))
    status_label = f"Dispatched {sent_count} notice(s) on {today_str} at {time_str}"
    if failed_count > 0:
        status_label += f" ({failed_count} failed)"
    set_setting("auto_overdue_last_status", status_label)

    msg = f"Overdue notices dispatched: {sent_count} successfully sent, {failed_count} failed."
    print(f"[Overdue-Service] {msg}")

    return (sent_count > 0 or failed_count == 0), {
        "dry_run": False,
        "message": msg,
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:5]
    }


def check_and_run_daily_overdue_notices():
    """
    Called periodically (every 10 minutes) by background scheduler.
    Safely executes ONLY if active and local IST time is >= scheduled hour (default 9:00 AM IST)
    and today's run has not been executed yet.
    """
    if not is_auto_overdue_active():
        # Safely skip when paused (as is the case with fake test data)
        return None, "Automated overdue notices are paused (safe mode)"

    now_ist = get_ist_now()
    sched_hour = int(get_setting("auto_overdue_email_hour", "9") or "9")

    if now_ist.hour >= sched_hour:
        today_str = now_ist.strftime("%Y-%m-%d")
        last_date = get_setting("auto_overdue_last_run_date", "")
        if last_date == today_str:
            return None, "Overdue notices already processed today"

        set_setting("auto_overdue_last_run_date", today_str)
        print(f"[Overdue-AutoPilot] IST time is {now_ist.strftime('%I:%M %p')}. Triggering scheduled overdue notices...")
        ok, res = dispatch_overdue_emails(dry_run=False, force=False)
        return ok, res.get("message", "Completed")

    return None, f"Not yet {sched_hour}:00 AM IST or already dispatched"

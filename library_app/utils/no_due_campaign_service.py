"""
Auto-Pilot Daily Dispatch Service for No Due Certificates
Allows the admin to click once — sends today's quota (e.g., 280-300 emails),
and automatically dispatches the next batch every morning at 6:00 AM IST
(right after Brevo's daily quota resets at 5:30 AM IST / 00:00 UTC) until all patrons are completed.
"""

import os
import time
from datetime import datetime, timezone, timedelta
from library_app.database import (
    get_setting, set_setting, get_all_cleared_patrons,
    get_no_due_bulk_summary, check_patron_no_due_status,
    mark_patron_no_due_emailed
)
from library_app.utils.no_due_pdf import generate_no_due_certificate_pdf
from library_app.utils.email_utils import send_no_due_certificate_email

IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    """Current datetime in Indian Standard Time (UTC+5:30)."""
    return datetime.now(IST)


def is_campaign_active() -> bool:
    """Check if the automated daily campaign is currently active."""
    return get_setting("no_due_auto_campaign_active", "0") == "1"


def get_campaign_status() -> dict:
    """Return complete status of the auto-pilot daily campaign."""
    active = is_campaign_active()
    daily_limit = int(get_setting("no_due_auto_campaign_daily_limit", "280") or "280")
    last_run_date = get_setting("no_due_auto_campaign_last_run_date", "")
    last_run_time = get_setting("no_due_auto_campaign_last_run_time", "")
    last_sent_count = int(get_setting("no_due_auto_campaign_last_sent_count", "0") or "0")
    status_msg = get_setting("no_due_auto_campaign_status_msg", "Idle")
    cert_date = get_setting("no_due_auto_campaign_cert_date", "") or datetime.now().strftime("%d-%m-%Y")
    patron_type = get_setting("no_due_auto_campaign_patron_type", "all")

    summary = get_no_due_bulk_summary()
    pending = summary.get("pending_to_email", 0)
    already_emailed = summary.get("already_emailed", 0)
    total_eligible = summary.get("cleared_with_email", 0)

    import math
    days_remaining = math.ceil(pending / daily_limit) if (pending > 0 and daily_limit > 0) else 0

    now_ist = get_ist_now()
    today_str = now_ist.strftime("%Y-%m-%d")
    ran_today = (last_run_date == today_str)

    if active:
        if pending == 0:
            next_run_desc = "Campaign Completed"
        elif ran_today:
            next_run_desc = "Tomorrow at 6:00 AM IST (after Brevo quota resets)"
        else:
            next_run_desc = "Scheduled to run today"
    else:
        next_run_desc = "Not active"

    return {
        "active": active,
        "daily_limit": daily_limit,
        "last_run_date": last_run_date,
        "last_run_time": last_run_time,
        "last_sent_count": last_sent_count,
        "status_msg": status_msg,
        "cert_date": cert_date,
        "patron_type": patron_type,
        "total_eligible": total_eligible,
        "already_emailed": already_emailed,
        "pending_in_queue": pending,
        "days_remaining": days_remaining,
        "ran_today": ran_today,
        "next_run_desc": next_run_desc
    }


def start_auto_campaign(daily_limit: int = 280, cert_date: str = None, patron_type: str = "all") -> dict:
    """Activate the auto-pilot daily campaign."""
    cert_date = cert_date or datetime.now().strftime("%d-%m-%Y")
    daily_limit = max(10, min(300, daily_limit or 280))

    set_setting("no_due_auto_campaign_active", "1")
    set_setting("no_due_auto_campaign_daily_limit", str(daily_limit))
    set_setting("no_due_auto_campaign_cert_date", cert_date)
    set_setting("no_due_auto_campaign_patron_type", patron_type)
    set_setting("no_due_auto_campaign_status_msg", f"Auto-pilot active: sending up to {daily_limit} emails daily at 6:00 AM IST.")

    return get_campaign_status()


def stop_auto_campaign() -> dict:
    """Pause/stop the auto-pilot campaign."""
    set_setting("no_due_auto_campaign_active", "0")
    set_setting("no_due_auto_campaign_status_msg", "Auto-pilot campaign paused by administrator.")
    return get_campaign_status()


def dispatch_campaign_batch(limit: int = None) -> tuple[bool, int, str]:
    """
    Process today's batch of No Due certificates.
    Sends up to limit (or configured daily_limit) emails to eligible patrons with 0 dues.
    Returns (success: bool, sent_count: int, message: str).
    """
    now_ist = get_ist_now()
    today_str = now_ist.strftime("%Y-%m-%d")
    time_display = now_ist.strftime("%I:%M %p IST")

    configured_limit = int(get_setting("no_due_auto_campaign_daily_limit", "280") or "280")
    batch_limit = limit if (limit and limit > 0) else configured_limit
    cert_date = get_setting("no_due_auto_campaign_cert_date", "") or now_ist.strftime("%d-%m-%Y")
    patron_type = get_setting("no_due_auto_campaign_patron_type", "all")
    filter_type = None if patron_type in ("all", "", "both") else patron_type

    # Fetch unemailed cleared patrons
    cleared = get_all_cleared_patrons(filter_type, only_unemailed=True)
    eligible = [p for p in cleared if (p.get("email") or p.get("parent_email"))]

    if not eligible:
        set_setting("no_due_auto_campaign_active", "0")
        msg = "All eligible cleared patrons have received their No Due certificates!"
        set_setting("no_due_auto_campaign_status_msg", msg)
        print(f"[NoDue-AutoPilot] {msg}")
        return True, 0, msg

    to_process = eligible[:batch_limit]
    print(f"[NoDue-AutoPilot] Starting dispatch of {len(to_process)} certificates (Daily Limit: {batch_limit})...")

    sent_count = 0
    fail_count = 0
    quota_hit = False
    quota_err_msg = ""

    for p in to_process:
        pid = p["id"]
        reg = p.get("register_number") or p.get("barcode")
        recipient = (p.get("email") or p.get("parent_email") or "").strip()

        if not recipient:
            continue

        try:
            # Verification safety check
            status_check = check_patron_no_due_status(reg)
            if status_check.get("has_due"):
                continue

            cert_id = status_check.get("certificate_id")
            pdf_bytes = generate_no_due_certificate_pdf(p, cert_date=cert_date, cert_id=cert_id)
            ok, err = send_no_due_certificate_email(p, pdf_bytes, cert_id, to_email=recipient)

            if ok:
                sent_count += 1
                mark_patron_no_due_emailed(pid, cert_id, recipient, success=True)
                print(f"[NoDue-AutoPilot] Sent ({sent_count}/{len(to_process)}): {p.get('name')} -> {recipient}")
            else:
                fail_count += 1
                mark_patron_no_due_emailed(pid, cert_id, recipient, success=False, err_msg=err)
                print(f"[NoDue-AutoPilot] Failed for {p.get('name')}: {err}")

                err_lower = str(err).lower()
                if any(k in err_lower for k in ["429", "quota", "limit exceeded", "exceeded your daily", "credit", "rate limit"]):
                    quota_hit = True
                    quota_err_msg = str(err)
                    break

            # Polite pacing between Brevo HTTP API calls
            time.sleep(0.35)

        except Exception as e:
            fail_count += 1
            print(f"[NoDue-AutoPilot] Exception for patron {pid}: {e}")

    # Update state
    set_setting("no_due_auto_campaign_last_run_date", today_str)
    set_setting("no_due_auto_campaign_last_run_time", time_display)
    set_setting("no_due_auto_campaign_last_sent_count", str(sent_count))

    # Re-evaluate remaining
    summary = get_no_due_bulk_summary()
    remaining = summary.get("pending_to_email", 0)

    if remaining == 0:
        set_setting("no_due_auto_campaign_active", "0")
        msg = f"Completed! Sent {sent_count} certificates today. All patrons cleared!"
    elif quota_hit:
        msg = f"Quota reached ({quota_err_msg}). Dispatched {sent_count} certificates today. {remaining} remaining — auto-resumes tomorrow at 6:00 AM IST."
    else:
        msg = f"Dispatched today's batch of {sent_count} certificates. {remaining} remaining in queue — next batch tomorrow at 6:00 AM IST."

    set_setting("no_due_auto_campaign_status_msg", msg)
    print(f"[NoDue-AutoPilot] {msg}")

    return (not quota_hit), sent_count, msg


def check_and_run_daily_campaign():
    """
    Called periodically by background scheduler (every 10 minutes).
    If auto-pilot campaign is active and local IST time is >= 6:00 AM,
    and today's batch hasn't run yet, dispatches the next batch.
    """
    if not is_campaign_active():
        return None, "Auto-pilot campaign not active"

    now_ist = get_ist_now()
    if now_ist.hour >= 6:  # 6:00 AM IST or later (after Brevo resets at 5:30 AM IST)
        today_str = now_ist.strftime("%Y-%m-%d")
        last_date = get_setting("no_due_auto_campaign_last_run_date", "")
        if last_date == today_str:
            return None, "Today's daily batch already dispatched"

        print(f"[NoDue-AutoPilot] Time is {now_ist.strftime('%I:%M %p IST')}. Triggering scheduled 6:00 AM daily No Due dispatch...")
        return dispatch_campaign_batch()

    return None, "Not yet 6:00 AM IST"

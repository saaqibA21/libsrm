"""
Automated GitHub Cloud Backup for SRM EEE Library
Pushes daily database snapshot (library.db) to GitHub repository via REST API.
"""

import base64
import os
from datetime import datetime, timezone, timedelta
import requests

from library_app.database import get_setting, set_setting, DB_PATH

# Indian Standard Time (UTC +5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    """Get current datetime in Indian Standard Time."""
    return datetime.now(IST)


def get_github_backup_config():
    """Fetch current GitHub backup configuration."""
    token = get_setting("github_backup_token", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()

    repo = get_setting("github_backup_repo", "").strip() or os.environ.get("GITHUB_REPO", "").strip()
    if not repo:
        repo = "saaqibA21/libsrm"

    branch = get_setting("github_backup_branch", "").strip() or "main"
    return token, repo, branch


def push_database_to_github(commit_message=None) -> tuple[bool, str]:
    """
    Pushes the current library.db file to GitHub repository via GitHub REST API.
    Returns (success: bool, message: str).
    """
    token, repo, branch = get_github_backup_config()
    if not token:
        return False, "GitHub Personal Access Token not configured. Please add it in Settings > Cloud Auto-Backup."

    db_file_path = DB_PATH

    if not os.path.exists(db_file_path):
        return False, f"Database file not found at {db_file_path}"

    try:
        with open(db_file_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        return False, f"Error reading database file: {e}"

    b64_content = base64.b64encode(file_bytes).decode("utf-8")
    now_ist = get_ist_now().strftime("%d-%b-%Y %I:%M %p IST")
    if not commit_message:
        commit_message = f"Automated Daily Library Backup — {now_ist}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SRM-Library-AutoBackup"
    }

    # 1. Fetch current file SHA from GitHub
    sha = None
    try:
        get_url = f"https://api.github.com/repos/{repo}/contents/library.db?ref={branch}"
        r_get = requests.get(get_url, headers=headers, timeout=30)
        if r_get.status_code == 200:
            sha = r_get.json().get("sha")
        elif r_get.status_code != 404:
            err_msg = f"GitHub API check failed (HTTP {r_get.status_code})"
            set_setting("github_last_backup_status", err_msg)
            return False, err_msg
    except Exception as e:
        err_msg = f"Network error connecting to GitHub: {e}"
        set_setting("github_last_backup_status", err_msg)
        return False, err_msg

    # 2. Upload / update library.db on GitHub
    put_url = f"https://api.github.com/repos/{repo}/contents/library.db"
    payload = {
        "message": commit_message,
        "content": b64_content,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha

    try:
        r_put = requests.put(put_url, json=payload, headers=headers, timeout=60)
        if r_put.status_code in (200, 201):
            res_data = r_put.json()
            commit_sha = res_data.get("commit", {}).get("sha", "")[:7]
            today_str = get_ist_now().strftime("%Y-%m-%d")

            set_setting("github_last_backup_status", "Success")
            set_setting("github_last_backup_time", now_ist)
            set_setting("github_last_backup_date", today_str)
            set_setting("github_last_commit_sha", commit_sha)

            return True, f"Successfully pushed database to GitHub! Commit: {commit_sha} ({now_ist})"
        else:
            err_msg = f"GitHub API Error (HTTP {r_put.status_code}): {r_put.text[:200]}"
            set_setting("github_last_backup_status", f"Failed: HTTP {r_put.status_code}")
            return False, err_msg
    except Exception as e:
        err_msg = f"Failed to push to GitHub: {e}"
        set_setting("github_last_backup_status", f"Failed: {e}")
        return False, err_msg


def check_and_run_daily_backup():
    """
    Called periodically by background scheduler.
    If local IST time is >= 18:00 (6:00 PM IST) and backup hasn't run today, pushes backup.
    """
    now = get_ist_now()
    if now.hour >= 18:  # 6:00 PM or later IST
        today_str = now.strftime("%Y-%m-%d")
        last_date = get_setting("github_last_backup_date", "")
        if last_date != today_str:
            print(f"[Auto-Backup] Local time is {now.strftime('%I:%M %p IST')}. Triggering scheduled 6:00 PM daily backup...")
            ok, msg = push_database_to_github(f"Automated Daily Library Backup — {now.strftime('%d-%b-%Y')} (06:00 PM IST)")
            print(f"[Auto-Backup] Result: {ok} -> {msg}")
            return ok, msg
    return None, "Not yet 6:00 PM IST or already backed up today"

"""
SRM EEE Library Management System - Database Layer
SQLite-based storage for books, patrons, transactions, settings
"""

import sqlite3
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_db():
    conn = get_connection()
    c = conn.cursor()

    # Books table
    c.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            account_number TEXT,
            title TEXT NOT NULL,
            publisher TEXT,
            authors TEXT,
            edition TEXT,
            status TEXT DEFAULT 'available',
            added_date TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Patrons table (students + teachers)
    c.execute("""
        CREATE TABLE IF NOT EXISTS patrons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            register_number TEXT UNIQUE,
            name TEXT NOT NULL,
            patron_type TEXT DEFAULT 'student',
            designation TEXT,
            year TEXT,
            section TEXT,
            mobile TEXT,
            email TEXT,
            parent_mobile TEXT,
            parent_email TEXT,
            added_date TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Schema migration: ensure designation column exists
    try:
        c.execute("ALTER TABLE patrons ADD COLUMN designation TEXT")
    except Exception:
        pass

    # Schema migration: ensure no_due_emailed_at column exists in patrons
    try:
        c.execute("ALTER TABLE patrons ADD COLUMN no_due_emailed_at TEXT")
    except Exception:
        pass

    # No Due certificate email dispatch logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS no_due_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patron_id INTEGER NOT NULL,
            cert_id TEXT,
            sent_to_email TEXT,
            sent_at TEXT DEFAULT (datetime('now', 'localtime')),
            status TEXT DEFAULT 'sent',
            error_message TEXT,
            FOREIGN KEY (patron_id) REFERENCES patrons(id)
        )
    """)

    # Transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            patron_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            issue_time TEXT,
            due_date TEXT NOT NULL,
            return_date TEXT,
            return_time TEXT,
            fine_amount REAL DEFAULT 0.0,
            fine_paid INTEGER DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'issued',
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (patron_id) REFERENCES patrons(id)
        )
    """)

    # Schema migration: ensure issue_time and return_time exist in transactions
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN issue_time TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN return_time TEXT")
    except Exception:
        pass

    # Schema migration: replace 'TF Details' / 'NT Details' in patrons.section with their designation
    try:
        c.execute("""
            UPDATE patrons 
            SET section = designation 
            WHERE patron_type = 'teacher' 
              AND designation IS NOT NULL 
              AND designation != ''
              AND (section LIKE '%TF Details%' OR section LIKE '%NT Details%' OR section = '' OR section IS NULL)
        """)
    except Exception:
        pass

    # 1. Strictly restore all teaching faculty & staff (faculty IDs, Chairperson, Professor, TF Details, TC10 barcodes)
    try:
        c.execute("""
            UPDATE patrons 
            SET patron_type = 'teacher', year = ''
            WHERE barcode LIKE 'TC10%' 
               OR (length(COALESCE(register_number,'')) <= 6 AND register_number GLOB '[0-9]*')
               OR UPPER(COALESCE(designation,'')) LIKE '%PROF%'
               OR UPPER(COALESCE(designation,'')) LIKE '%CHAIRPERSON%'
               OR UPPER(COALESCE(section,'')) LIKE '%CHAIRPERSON%'
               OR UPPER(COALESCE(section,'')) LIKE '%TF DETAILS%'
               OR UPPER(COALESCE(section,'')) LIKE '%NT FACULTY%'
        """)
        conn.commit()
    except Exception:
        pass

    # 2. Schema migration: update Research Scholars (Year = 'RS', RS Details sheet, or scholar register numbers)
    try:
        c.execute("""
            UPDATE patrons 
            SET patron_type = 'research_scholar'
            WHERE patron_type != 'teacher'
              AND barcode NOT LIKE 'TC10%'
              AND (
                  UPPER(COALESCE(year,'')) = 'RS' 
               OR UPPER(COALESCE(section,'')) LIKE '%RS DETAILS%'
               OR UPPER(COALESCE(section,'')) = 'RS'
               OR (UPPER(COALESCE(designation,'')) LIKE '%SCHOLAR%' AND UPPER(COALESCE(designation,'')) NOT LIKE '%PROF%')
               OR barcode LIKE 'RS%'
              )
        """)
        c.execute("""
            UPDATE patrons 
            SET year = 'RS'
            WHERE patron_type = 'research_scholar'
              AND (year IS NULL OR year = '' OR year = '—' OR year = '-')
        """)
        conn.commit()
    except Exception:
        pass

    # Settings table
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Default settings
    defaults = {
        "loan_period_student": "15",
        "loan_period_teacher": "30",
        "fine_per_day": "2.0",
        "library_name": "SRM EEE Department Library",
        "staff_pin": "1234",
        "email_host": "smtp.gmail.com",
        "email_port": "587",
        "email_user": "",
        "email_password": "",
        "email_from": "",
        "brevo_sender_email": "saaqibheroindia@gmail.com",
        "email_reply_to": "srmeeelibraray@gmail.com",
        "github_backup_token": "",
        "github_backup_repo": "saaqibA21/libsrm",
        "github_backup_branch": "main",
        "github_last_backup_status": "Active",
        "library_hours_morning": "9:30 AM – 12:30 PM",
        "library_hours_afternoon": "1:30 PM – 4:30 PM",
        "library_hours_display": "9:30 AM – 12:30 PM & 1:30 PM – 4:30 PM",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


# ─── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    val = row["value"] if row else None
    if val is not None and str(val).strip():
        return str(val).strip()
    # Fallback to Environment Variables (e.g. EMAIL_USER, EMAIL_PASSWORD, etc.)
    env_key = key.upper()
    env_val = os.environ.get(env_key)
    if env_val is not None and str(env_val).strip():
        return str(env_val).strip()
    return str(val).strip() if (val is not None and str(val).strip()) else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    res = {r["key"]: r["value"] for r in rows}
    for k in ["brevo_api_key", "brevo_sender_email", "email_reply_to", "email_user", "email_password", "email_host", "email_port", "email_from", "staff_pin", "library_name"]:
        if not res.get(k) and os.environ.get(k.upper()):
            res[k] = os.environ.get(k.upper())
    return res


# ─── Edition Normalization ─────────────────────────────────────────────────────

WORDS_TO_NUM = {
    'first': 1, '1st': 1, '1': 1, 'one': 1,
    'second': 2, '2nd': 2, '2': 2, 'secong': 2, 'two': 2,
    'third': 3, '3rd': 3, '3': 3, 'three': 3,
    'fourth': 4, '4th': 4, '4': 4, 'four': 4,
    'fifth': 5, '5th': 5, '5': 5, 'five': 5, '5e': 5,
    'sixth': 6, '6th': 6, '6': 6, 'six': 6,
    'seventh': 7, '7th': 7, '7': 7, 'seven': 7,
    'eighth': 8, '8th': 8, '8': 8, 'eight': 8,
    'ninth': 9, '9th': 9, '9': 9, 'nineth': 9, 'nine': 9,
    'tenth': 10, '10th': 10, '10': 10, 'ten': 10,
    'eleventh': 11, '11th': 11, '11': 11,
    'twelfth': 12, '12th': 12, '12': 12, 'twelveth': 12, 'twelth': 12,
    'thirteenth': 13, '13th': 13, '13': 13, 'thirtenth': 13,
    'fourteenth': 14, '14th': 14, '14': 14,
    'fifteenth': 15, '15th': 15, '15': 15,
    'sixteenth': 16, '16th': 16, '16': 16,
    'seventeenth': 17, '17th': 17, '17': 17,
    'eighteenth': 18, '18th': 18, '18': 18,
    'nineteenth': 19, '19th': 19, '19': 19,
    'twentieth': 20, '20th': 20, '20': 20,
    'twenty first': 21, '21st': 21, '21': 21,
    'twenty second': 22, 'twenty-second': 22, '22nd': 22, '22': 22,
    'twenty third': 23, '23rd': 23, '23': 23,
    'twenty fourth': 24, '24th': 24, '24': 24,
    'twenty fifth': 25, '25th': 25, '25': 25,
    'twenty sixth': 26, '26th': 26, '26': 26,
    'twenty seven': 27, '27th': 27, '27': 27,
}


def ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def normalize_edition(raw):
    """
    Standardize edition names into a single clean format:
    e.g. 'THIRD' / '3' -> '3rd Edition', 'SECOND' / '2' -> '2nd Edition',
    'NIL' -> '', 'Revised' -> 'Revised Edition'.
    """
    if not raw:
        return ""
    s = str(raw).strip()
    if s.upper() in ("NIL", "NONE", "NA", "N/A", "-", "NULL", "EMPTY"):
        return ""
    clean = s.lower().replace("-", " ").strip()
    is_reprint = "reprint" in clean
    core = clean.replace("edition", "").replace("reprint", "").replace("printing", "").strip()
    if core in WORDS_TO_NUM:
        n = WORDS_TO_NUM[core]
        ord_str = ordinal(n)
        return f"{ord_str} Reprint" if is_reprint else f"{ord_str} Edition"
    m = re.match(r"^(\d+)(?:st|nd|rd|th)?(?:\s*(?:ed|edition|reprint))?$", clean, re.I)
    if m:
        n = int(m.group(1))
        ord_str = ordinal(n)
        return f"{ord_str} Reprint" if is_reprint else f"{ord_str} Edition"
    if "revised" in clean:
        return "Revised Edition"
    if "international" in clean:
        return "International Edition"
    if "enhanced" in clean:
        return "Enhanced Edition"
    return s.title()


def _format_book_dict(d):
    """Ensure book dict has normalized edition and clean fields."""
    if not d:
        return d
    if "edition" in d:
        d["edition"] = normalize_edition(d.get("edition"))
    return d


# ─── Books ─────────────────────────────────────────────────────────────────────

def add_book(barcode, title, publisher="", authors="", edition="", account_number=""):
    edition = normalize_edition(edition)
    conn = get_connection()
    if not barcode:
        clean_acc = (account_number or "").strip()
        if clean_acc:
            barcode = f"BK{clean_acc}"
        else:
            barcode = f"BK{int(datetime.now().timestamp() * 1000)}"
    try:
        conn.execute("""
            INSERT INTO books (barcode, account_number, title, publisher, authors, edition)
            VALUES (?,?,?,?,?,?)
        """, (barcode, account_number, title, publisher, authors, edition))
        conn.commit()
        return True, f"Book added successfully! Barcode: {barcode}"
    except sqlite3.IntegrityError:
        return False, "Barcode already exists"
    finally:
        conn.close()


def update_book(book_id, title, publisher, authors, edition, account_number):
    edition = normalize_edition(edition)
    conn = get_connection()
    conn.execute("""
        UPDATE books SET title=?, publisher=?, authors=?, edition=?, account_number=?
        WHERE id=?
    """, (title, publisher, authors, edition, account_number, book_id))
    conn.commit()
    conn.close()


def delete_book(book_id):
    conn = get_connection()
    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()


def get_book_by_barcode(barcode):
    """
    Lookup a book by barcode or accession / account number.
    Handles case-insensitivity, spaces, and 'BK' prefix variations.
    """
    if not barcode:
        return None
    ident = str(barcode).strip()
    if not ident:
        return None

    conn = get_connection()
    clean = ident.replace(" ", "").replace("-", "")

    row = conn.execute("""
        SELECT * FROM books
        WHERE UPPER(barcode) = UPPER(?)
           OR UPPER(account_number) = UPPER(?)
           OR UPPER(barcode) = UPPER(?)
           OR UPPER(account_number) = UPPER(?)
    """, (ident, ident, clean, clean)).fetchone()

    if not row:
        stripped_bk = clean[2:] if clean.upper().startswith("BK") else clean
        row = conn.execute("""
            SELECT * FROM books
            WHERE UPPER(barcode) = UPPER(?)
               OR UPPER(barcode) = UPPER(?)
               OR UPPER(account_number) = UPPER(?)
        """, (f"BK{clean}", stripped_bk, stripped_bk)).fetchone()

    conn.close()
    return _format_book_dict(dict(row)) if row else None


def get_book_by_id(book_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    conn.close()
    return _format_book_dict(dict(row)) if row else None


def search_books(query="", status_filter=None):
    conn = get_connection()
    q = f"%{query}%"
    sql = """
        SELECT * FROM books
        WHERE (title LIKE ? OR authors LIKE ? OR barcode LIKE ? OR account_number LIKE ?)
    """
    params = [q, q, q, q]
    if status_filter:
        sql += " AND status=?"
        params.append(status_filter)
    sql += " ORDER BY title"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_format_book_dict(dict(r)) for r in rows]


def get_all_books():
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM books 
        ORDER BY 
            CASE WHEN account_number GLOB '[0-9]*' THEN 0 ELSE 1 END,
            CAST(account_number AS INTEGER),
            account_number,
            title
    """).fetchall()
    conn.close()
    return [_format_book_dict(dict(r)) for r in rows]


def count_books():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available = conn.execute("SELECT COUNT(*) FROM books WHERE status='available'").fetchone()[0]
    issued = conn.execute("SELECT COUNT(*) FROM books WHERE status='issued'").fetchone()[0]
    conn.close()
    return {"total": total, "available": available, "issued": issued}


# ─── Patrons ───────────────────────────────────────────────────────────────────

def add_patron(barcode, register_number, name, patron_type="student",
               designation="", year="", section="", mobile="", email="",
               parent_mobile="", parent_email=""):
    conn = get_connection()
    if (year or "").strip().upper() == "RS" and patron_type != "teacher":
        patron_type = "research_scholar"
    if patron_type == "research_scholar" and not (year or "").strip():
        year = "RS"
    if not barcode:
        clean_reg = (register_number or "").strip().replace(" ", "").replace("/", "")
        if patron_type == "student":
            prefix = "ST"
        elif patron_type == "research_scholar":
            prefix = "RS"
        else:
            prefix = "TC"
        if clean_reg:
            barcode = f"{prefix}{clean_reg}"
        else:
            barcode = f"{prefix}{int(datetime.now().timestamp() * 1000)}"
    try:
        conn.execute("""
            INSERT INTO patrons
            (barcode, register_number, name, patron_type, designation, year, section,
             mobile, email, parent_mobile, parent_email)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (barcode, register_number, name, patron_type, designation, year, section,
              mobile, email, parent_mobile, parent_email))
        conn.commit()
        return True, f"Patron added successfully! Barcode: {barcode}"
    except sqlite3.IntegrityError as e:
        return False, f"Duplicate entry: {e}"
    finally:
        conn.close()


def update_patron(patron_id, name, patron_type, year="", section="", mobile="", email="",
                  parent_mobile="", parent_email="", designation=""):
    conn = get_connection()
    if (year or "").strip().upper() == "RS" and patron_type != "teacher":
        patron_type = "research_scholar"
    if patron_type == "research_scholar" and not (year or "").strip():
        year = "RS"
    conn.execute("""
        UPDATE patrons SET name=?, patron_type=?, designation=?, year=?, section=?,
        mobile=?, email=?, parent_mobile=?, parent_email=?
        WHERE id=?
    """, (name, patron_type, designation, year, section, mobile, email,
          parent_mobile, parent_email, patron_id))
    conn.commit()
    conn.close()


def delete_patron(patron_id):
    conn = get_connection()
    conn.execute("DELETE FROM patrons WHERE id=?", (patron_id,))
    conn.commit()
    conn.close()


def get_patron_by_barcode(barcode):
    """
    Lookup a patron by barcode, register number, staff ID, or mobile number.
    Handles case-insensitivity, spaces, and 'ST'/'TC'/'RS' prefix variations.
    """
    if not barcode:
        return None
    ident = str(barcode).strip()
    if not ident:
        return None

    conn = get_connection()
    clean = ident.replace(" ", "").replace("-", "")

    # 1. Direct or case-insensitive match on barcode or register_number
    row = conn.execute("""
        SELECT * FROM patrons
        WHERE UPPER(barcode) = UPPER(?)
           OR UPPER(register_number) = UPPER(?)
           OR UPPER(barcode) = UPPER(?)
           OR UPPER(register_number) = UPPER(?)
    """, (ident, ident, clean, clean)).fetchone()

    # 2. Try prefix variations (e.g. user entered reg no without ST/TC/RS, or with ST/TC/RS)
    if not row:
        stripped_prefix = clean[2:] if clean.upper().startswith(("ST", "TC", "RS")) else clean
        row = conn.execute("""
            SELECT * FROM patrons
            WHERE UPPER(barcode) = UPPER(?)
               OR UPPER(barcode) = UPPER(?)
               OR UPPER(barcode) = UPPER(?)
               OR UPPER(barcode) = UPPER(?)
               OR UPPER(register_number) = UPPER(?)
               OR UPPER(register_number) = UPPER(?)
        """, (
            f"ST{clean}",
            f"RS{clean}",
            f"TC{clean}",
            stripped_prefix,
            clean,
            stripped_prefix
        )).fetchone()

    # 3. Fallback: match on mobile number or email
    if not row:
        row = conn.execute("""
            SELECT * FROM patrons
            WHERE mobile = ? OR email = ? OR UPPER(email) = UPPER(?)
        """, (clean, ident, ident)).fetchone()

    conn.close()
    return dict(row) if row else None


def get_patron_by_id(patron_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM patrons WHERE id=?", (patron_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search_patrons(query="", patron_type=None):
    conn = get_connection()
    q = f"%{query}%"
    sql = """
        SELECT * FROM patrons
        WHERE (name LIKE ? OR register_number LIKE ? OR barcode LIKE ? OR mobile LIKE ?)
    """
    params = [q, q, q, q]
    if patron_type:
        if patron_type == 'research_scholar':
            sql += " AND patron_type='research_scholar'"
        elif patron_type == 'student':
            sql += " AND patron_type='student'"
        elif patron_type == 'teacher':
            sql += " AND patron_type='teacher'"
        else:
            sql += " AND patron_type=?"
            params.append(patron_type)
    sql += " ORDER BY name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_patrons():
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM patrons
        ORDER BY 
            CASE patron_type WHEN 'teacher' THEN 1 WHEN 'research_scholar' THEN 2 ELSE 3 END,
            CASE year WHEN 'I' THEN 1 WHEN 'II' THEN 2 WHEN 'III' THEN 3 WHEN 'IV' THEN 4 ELSE 5 END,
            section,
            register_number,
            name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_patrons():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    teachers = conn.execute("SELECT COUNT(*) FROM patrons WHERE patron_type='teacher'").fetchone()[0]
    scholars = conn.execute("SELECT COUNT(*) FROM patrons WHERE patron_type='research_scholar'").fetchone()[0]
    students = conn.execute("SELECT COUNT(*) FROM patrons WHERE patron_type='student'").fetchone()[0]
    conn.close()
    return {"total": total, "students": students, "teachers": teachers, "scholars": scholars}


# ─── Transactions ──────────────────────────────────────────────────────────────

def format_time_str(time_val=None):
    """Normalize time string to standard 'HH:MM AM/PM' or 'HH:MM:SS AM/PM' format or current time."""
    if not time_val:
        return datetime.now().strftime("%I:%M:%S %p")
    t = str(time_val).strip()
    if not t:
        return datetime.now().strftime("%I:%M:%S %p")
    if "AM" in t.upper() or "PM" in t.upper():
        return t.upper()
    for fmt, out_fmt in (("%H:%M:%S", "%I:%M:%S %p"), ("%H:%M", "%I:%M %p"), ("%I:%M", "%I:%M %p")):
        try:
            return datetime.strptime(t, fmt).strftime(out_fmt)
        except ValueError:
            pass
    return t


def issue_book(book_id, patron_id, patron_type="student", issue_date=None, due_date=None, issue_time=None):
    conn = get_connection()
    try:
        # Check book availability
        book = conn.execute("SELECT status FROM books WHERE id=?", (book_id,)).fetchone()
        if not book or book["status"] != "available":
            return False, "Book is not available for issue"

        # Check if patron already has this book
        existing = conn.execute("""
            SELECT id FROM transactions WHERE book_id=? AND patron_id=? AND status='issued'
        """, (book_id, patron_id)).fetchone()
        if existing:
            return False, "Patron already has this book"

        loan_key = "loan_period_teacher" if patron_type in ("teacher", "faculty", "staff") else "loan_period_student"
        val_row = conn.execute("SELECT value FROM settings WHERE key=?", (loan_key,)).fetchone()
        try:
            loan_days = int(val_row["value"]) if val_row and val_row["value"] else (30 if loan_key == "loan_period_teacher" else 15)
        except (ValueError, TypeError):
            loan_days = 30 if loan_key == "loan_period_teacher" else 15

        now_dt = datetime.now()
        if not issue_date:
            issue_date = now_dt.strftime("%Y-%m-%d")

        issue_time = format_time_str(issue_time)

        if not due_date:
            try:
                base_dt = datetime.strptime(issue_date, "%Y-%m-%d")
            except Exception:
                base_dt = now_dt
            due_date = (base_dt + timedelta(days=loan_days)).strftime("%Y-%m-%d")

        conn.execute("""
            INSERT INTO transactions (book_id, patron_id, issue_date, issue_time, due_date, status)
            VALUES (?,?,?,?,?,'issued')
        """, (book_id, patron_id, issue_date, issue_time, due_date))

        conn.execute("UPDATE books SET status='issued' WHERE id=?", (book_id,))
        conn.commit()
        return True, f"Book issued successfully. Due date: {due_date}"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def return_book(transaction_id, return_date=None, return_time=None):
    conn = get_connection()
    try:
        txn = conn.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not txn:
            return False, "Transaction not found"
        if txn["status"] == "returned":
            return False, "Book already returned"

        now_dt = datetime.now()
        if not return_date:
            return_date = now_dt.strftime("%Y-%m-%d")

        return_time = format_time_str(return_time)

        try:
            ret_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
        except Exception:
            ret_date_obj = now_dt
            return_date = ret_date_obj.strftime("%Y-%m-%d")

        due_date = datetime.strptime(txn["due_date"], "%Y-%m-%d")

        fine = 0.0
        if ret_date_obj > due_date:
            overdue_days = (ret_date_obj - due_date).days
            fine_per_day = float(conn.execute(
                "SELECT value FROM settings WHERE key='fine_per_day'"
            ).fetchone()["value"])
            fine = overdue_days * fine_per_day

        conn.execute("""
            UPDATE transactions SET return_date=?, return_time=?, fine_amount=?, status='returned'
            WHERE id=?
        """, (return_date, return_time, fine, transaction_id))

        conn.execute("UPDATE books SET status='available' WHERE id=?", (txn["book_id"],))
        conn.commit()
        return True, fine
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_active_transaction_by_book(book_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               p.name as patron_name, p.register_number, p.email as patron_email,
               p.patron_type
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN patrons p ON t.patron_id = p.id
        WHERE t.book_id=? AND t.status='issued'
    """, (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_patron_active_books(patron_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               b.authors as book_authors
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.patron_id=? AND t.status='issued'
        ORDER BY t.due_date
    """, (patron_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_active_transactions():
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               p.name as patron_name, p.register_number, p.patron_type,
               p.designation as patron_designation,
               p.email as patron_email
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN patrons p ON t.patron_id = p.id
        WHERE t.status='issued'
        ORDER BY t.due_date
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_overdue_transactions():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               p.name as patron_name, p.register_number, p.patron_type,
               p.designation as patron_designation,
               p.email as patron_email, p.mobile as patron_mobile
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN patrons p ON t.patron_id = p.id
        WHERE t.status='issued' AND t.due_date < ?
        ORDER BY t.due_date
    """, (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transaction_history(limit=200):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               p.name as patron_name, p.register_number, p.patron_type,
               p.designation as patron_designation
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN patrons p ON t.patron_id = p.id
        ORDER BY t.id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_patron_history(patron_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode, b.account_number as book_account_number
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.patron_id=?
        ORDER BY t.id DESC
    """, (patron_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_transactions_by_date(from_date=None, to_date=None, date_type="issue_date",
                                query="", status="all", limit=500):
    """
    Search circulation transactions with date range filters, keyword search, and status filter.
    Returns (transactions_list, summary_stats_dict).
    """
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    fine_rate = 2.0
    try:
        fr = conn.execute("SELECT value FROM settings WHERE key='fine_per_day'").fetchone()
        if fr: fine_rate = float(fr["value"])
    except Exception:
        pass

    sql = """
        SELECT t.*,
               b.title as book_title, b.barcode as book_barcode, b.account_number as book_acc,
               p.name as patron_name, p.register_number as patron_reg, p.patron_type,
               p.designation as patron_designation, p.year as patron_year, p.section as patron_section,
               p.mobile as patron_mobile, p.email as patron_email
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN patrons p ON t.patron_id = p.id
        WHERE 1=1
    """
    params = []

    # Date field selection
    field = "t.issue_date"
    if date_type == "return_date":
        field = "t.return_date"
    elif date_type == "due_date":
        field = "t.due_date"

    if from_date and from_date.strip():
        sql += f" AND date({field}) >= date(?)"
        params.append(from_date.strip())
    if to_date and to_date.strip():
        sql += f" AND date({field}) <= date(?)"
        params.append(to_date.strip())

    # Status filter
    if status == "issued":
        sql += " AND t.status = 'issued'"
    elif status == "returned":
        sql += " AND t.status = 'returned'"
    elif status == "overdue":
        sql += f" AND t.status = 'issued' AND t.due_date < '{today}'"

    # Search keyword
    if query and query.strip():
        q = f"%{query.strip()}%"
        sql += """ AND (
            b.title LIKE ? OR b.barcode LIKE ? OR b.account_number LIKE ?
            OR p.name LIKE ? OR p.register_number LIKE ? OR p.barcode LIKE ?
            OR p.designation LIKE ?
        )"""
        params.extend([q, q, q, q, q, q, q])

    sql += f" ORDER BY {field} DESC, t.id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    today_dt = datetime.now()
    results = []
    total_fines = 0.0
    issued_count = 0
    returned_count = 0
    overdue_count = 0

    for r in rows:
        d = dict(r)
        due_dt = None
        try:
            due_dt = datetime.strptime(d["due_date"], "%Y-%m-%d")
        except Exception:
            pass

        if d["status"] == "issued":
            issued_count += 1
            if due_dt and due_dt < today_dt:
                overdue_count += 1
                d["is_overdue"] = True
                d["overdue_days"] = (today_dt - due_dt).days
                d["calculated_fine"] = d["overdue_days"] * fine_rate
            else:
                d["is_overdue"] = False
                d["overdue_days"] = 0
                d["calculated_fine"] = 0.0
        else:
            returned_count += 1
            d["is_overdue"] = False
            d["overdue_days"] = 0
            d["calculated_fine"] = float(d.get("fine_amount") or 0.0)

        d["fine_payable"] = 0.0 if d.get("fine_paid") else d.get("calculated_fine", 0.0)
        total_fines += d["fine_payable"]
        results.append(d)

    summary = {
        "total": len(results),
        "issued": issued_count,
        "returned": returned_count,
        "overdue": overdue_count,
        "total_fines": total_fines
    }
    return results, summary


# ─── Analytics / Reports ───────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    today_dt = datetime.now()
    today = today_dt.date()
    today_str = today.strftime("%Y-%m-%d")

    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = conn.execute("SELECT COUNT(*) FROM books WHERE status='available'").fetchone()[0]
    issued_books = conn.execute("SELECT COUNT(*) FROM books WHERE status='issued'").fetchone()[0]
    total_patrons = conn.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    overdue = conn.execute("SELECT COUNT(*) FROM transactions WHERE status='issued' AND due_date < ?", (today_str,)).fetchone()[0]
    issued_today = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(issue_date)=date('now','localtime')").fetchone()[0]
    returned_today = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(return_date)=date('now','localtime')").fetchone()[0]

    # Fine rate per day
    fine_val = conn.execute("SELECT value FROM settings WHERE key='fine_per_day'").fetchone()
    fine_rate = float(fine_val["value"]) if fine_val and fine_val["value"] else 2.0

    # 1. Unpaid fines from already returned books
    unpaid_returned = conn.execute("""
        SELECT COALESCE(SUM(fine_amount), 0)
        FROM transactions
        WHERE status='returned' AND fine_paid=0 AND fine_amount > 0
    """).fetchone()[0] or 0.0

    # 2. Accumulated active fines on currently issued overdue books
    overdue_txns = conn.execute("""
        SELECT due_date
        FROM transactions
        WHERE status='issued' AND due_date < ?
    """, (today_str,)).fetchall()

    active_overdue_fines = 0.0
    for r in overdue_txns:
        try:
            due_dt = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
            if due_dt < today:
                active_overdue_fines += (today - due_dt).days * fine_rate
        except Exception:
            pass

    total_fines = round(float(unpaid_returned) + active_overdue_fines, 2)

    conn.close()
    return {
        "total_books": total_books,
        "available_books": available_books,
        "issued_books": issued_books,
        "total_patrons": total_patrons,
        "overdue": overdue,
        "issued_today": issued_today,
        "returned_today": returned_today,
        "pending_fines": total_fines,
    }


def get_today_transactions():
    """Retrieve all circulation transactions issued or returned today."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT t.id, t.issue_date, t.issue_time, t.due_date, t.return_date, t.return_time, t.status, t.fine_amount,
               b.title as book_title, b.barcode as book_barcode, b.account_number as book_acc,
               p.name as patron_name, p.register_number as patron_reg, p.patron_type
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN patrons p ON t.patron_id = p.id
        WHERE date(t.issue_date) = date(?) OR date(t.return_date) = date(?)
        ORDER BY t.id DESC
    """, (today, today)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_most_borrowed_books(limit=10):
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.title, b.authors, b.barcode, COUNT(t.id) as borrow_count
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        GROUP BY t.book_id
        ORDER BY borrow_count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_most_active_patrons(limit=10):
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.name, p.register_number, p.patron_type, COUNT(t.id) as borrow_count
        FROM transactions t
        JOIN patrons p ON t.patron_id = p.id
        GROUP BY t.patron_id
        ORDER BY borrow_count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_book_borrow_stats(query="", limit=50):
    """Search how many times each book has been borrowed, who borrowed it, and its circulation status."""
    conn = get_connection()
    q = f"%{query}%"
    sql = """
        SELECT b.id, b.title, b.authors, b.barcode, b.account_number, b.status,
               COUNT(t.id) as times_borrowed,
               MAX(t.issue_date) as last_issued_date,
               (SELECT p.name FROM transactions t2 JOIN patrons p ON t2.patron_id = p.id 
                WHERE t2.book_id = b.id AND t2.status = 'issued' LIMIT 1) as current_borrower,
               (SELECT t2.due_date FROM transactions t2 
                WHERE t2.book_id = b.id AND t2.status = 'issued' LIMIT 1) as current_due_date,
               (SELECT GROUP_CONCAT(DISTINCT p.name || CASE WHEN p.register_number IS NOT NULL AND p.register_number != '' THEN ' (' || p.register_number || ')' ELSE '' END)
                FROM transactions t2 JOIN patrons p ON t2.patron_id = p.id 
                WHERE t2.book_id = b.id) as borrowers_list
        FROM books b
        LEFT JOIN transactions t ON b.id = t.book_id
        WHERE (b.title LIKE ? OR b.authors LIKE ? OR b.barcode LIKE ? OR b.account_number LIKE ?)
        GROUP BY b.id
        ORDER BY times_borrowed DESC, b.title ASC
        LIMIT ?
    """
    rows = conn.execute(sql, (q, q, q, q, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_book_borrowers(book_id):
    """Retrieve full borrowing history and borrowers list for a book."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.id, t.issue_date, t.issue_time, t.due_date, t.return_date, t.return_time, t.status, t.fine_amount,
               p.name as borrower_name, p.register_number as borrower_reg, p.patron_type, p.barcode as patron_barcode,
               p.year as borrower_year, p.section as borrower_section
        FROM transactions t
        LEFT JOIN patrons p ON t.patron_id = p.id
        WHERE t.book_id = ?
        ORDER BY t.id DESC
    """, (book_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_patron_borrow_stats(query="", limit=50):
    """Search how many books each patron has taken, with active loans and fines."""
    conn = get_connection()
    q = f"%{query}%"
    today_dt = datetime.now()
    today = today_dt.date()
    today_str = today.strftime("%Y-%m-%d")

    fine_val = conn.execute("SELECT value FROM settings WHERE key='fine_per_day'").fetchone()
    fine_rate = float(fine_val["value"]) if fine_val and fine_val["value"] else 2.0

    sql = """
        SELECT p.id, p.name, p.register_number, p.patron_type, p.year, p.section, p.barcode, p.email,
               COUNT(t.id) as total_books_taken,
               SUM(CASE WHEN t.status = 'issued' THEN 1 ELSE 0 END) as active_loans_count,
               SUM(CASE WHEN t.status = 'issued' AND t.due_date < ? THEN 1 ELSE 0 END) as overdue_count,
               SUM(CASE WHEN t.status = 'returned' AND t.fine_paid = 0 THEN t.fine_amount ELSE 0 END) as returned_unpaid_fines,
               MAX(t.issue_date) as last_borrowed_date
        FROM patrons p
        LEFT JOIN transactions t ON p.id = t.patron_id
        WHERE (p.name LIKE ? OR p.register_number LIKE ? OR p.barcode LIKE ? OR p.email LIKE ?)
        GROUP BY p.id
        ORDER BY total_books_taken DESC, p.name ASC
        LIMIT ?
    """
    rows = conn.execute(sql, (today_str, q, q, q, q, limit)).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        pid = d["id"]
        # Calculate active overdue fines for this patron
        active_overdue = conn.execute("""
            SELECT due_date FROM transactions
            WHERE patron_id = ? AND status = 'issued' AND due_date < ?
        """, (pid, today_str)).fetchall()

        active_fine = 0.0
        for ao in active_overdue:
            try:
                due_dt = datetime.strptime(ao["due_date"], "%Y-%m-%d").date()
                if due_dt < today:
                    active_fine += (today - due_dt).days * fine_rate
            except Exception:
                pass

        d["pending_fines"] = round(float(d.get("returned_unpaid_fines") or 0.0) + active_fine, 2)
        results.append(d)

    conn.close()
    return results


def mark_fine_paid(transaction_id, paid=1):
    conn = get_connection()
    conn.execute("UPDATE transactions SET fine_paid=? WHERE id=?", (1 if paid else 0, transaction_id))
    conn.commit()
    conn.close()


def search_books_with_availability(query="", status_filter=None, limit=60, offset=0):
    conn = get_connection()
    q = f"%{query.strip()}%"
    sql = """
        SELECT b.*, 
               t.id as active_transaction_id,
               t.issue_date,
               t.due_date as expected_available_date,
               p.name as borrower_name,
               p.register_number as borrower_reg
        FROM books b
        LEFT JOIN transactions t ON b.id = t.book_id AND t.status = 'issued'
        LEFT JOIN patrons p ON t.patron_id = p.id
        WHERE (b.title LIKE ? OR b.authors LIKE ? OR b.barcode LIKE ? OR b.account_number LIKE ? OR b.publisher LIKE ?)
    """
    params = [q, q, q, q, q]
    if status_filter == "available":
        sql += " AND b.status = 'available'"
    elif status_filter == "issued":
        sql += " AND b.status = 'issued'"

    sql += """
        ORDER BY 
            CASE WHEN b.account_number GLOB '[0-9]*' THEN 0 ELSE 1 END,
            CAST(b.account_number AS INTEGER),
            b.account_number,
            b.title
    """
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    now = datetime.now()
    results = []
    for r in rows:
        d = dict(r)
        exp = d.get("expected_available_date")
        if exp and d.get("status") == "issued":
            try:
                due_dt = datetime.strptime(exp, "%Y-%m-%d")
                days_left = (due_dt.date() - now.date()).days
                d["days_left"] = days_left
                d["is_overdue"] = days_left < 0
                if days_left > 1:
                    d["availability_badge"] = f"Expected back {due_dt.strftime('%d %b %Y')} ({days_left}d)"
                    d["availability_class"] = "badge-warning"
                elif days_left == 1:
                    d["availability_badge"] = f"Expected Tomorrow ({due_dt.strftime('%d %b')})"
                    d["availability_class"] = "badge-warning"
                elif days_left == 0:
                    d["availability_badge"] = "Due Today"
                    d["availability_class"] = "badge-warning"
                else:
                    d["availability_badge"] = f"Overdue by {abs(days_left)} days"
                    d["availability_class"] = "badge-danger"
            except Exception:
                d["availability_badge"] = f"Due: {exp}"
                d["availability_class"] = "badge-warning"
        else:
            d["days_left"] = None
            d["is_overdue"] = False
            d["availability_badge"] = "Available on Shelf"
            d["availability_class"] = "badge-success"
        results.append(_format_book_dict(d))
    return results


def count_search_books(query="", status_filter=None):
    conn = get_connection()
    q = f"%{query.strip()}%"
    sql = """
        SELECT COUNT(*) FROM books b
        WHERE (b.title LIKE ? OR b.authors LIKE ? OR b.barcode LIKE ? OR b.account_number LIKE ? OR b.publisher LIKE ?)
    """
    params = [q, q, q, q, q]
    if status_filter == "available":
        sql += " AND b.status = 'available'"
    elif status_filter == "issued":
        sql += " AND b.status = 'issued'"
    count = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return count


def get_book_with_full_details(book_id):
    conn = get_connection()
    book = conn.execute("""
        SELECT b.*, 
               t.id as active_transaction_id,
               t.issue_date,
               t.due_date as expected_available_date,
               p.name as borrower_name,
               p.register_number as borrower_reg
        FROM books b
        LEFT JOIN transactions t ON b.id = t.book_id AND t.status = 'issued'
        LEFT JOIN patrons p ON t.patron_id = p.id
        WHERE b.id = ?
    """, (book_id,)).fetchone()
    if not book:
        conn.close()
        return None

    d = _format_book_dict(dict(book))
    exp = d.get("expected_available_date")
    now = datetime.now()
    if exp and d.get("status") == "issued":
        try:
            due_dt = datetime.strptime(exp, "%Y-%m-%d")
            days_left = (due_dt.date() - now.date()).days
            d["days_left"] = days_left
            d["is_overdue"] = days_left < 0
            if days_left > 1:
                d["availability_badge"] = f"Expected return on {due_dt.strftime('%d %B %Y')} ({days_left} days remaining)"
                d["availability_class"] = "badge-warning"
            elif days_left == 1:
                d["availability_badge"] = f"Expected return tomorrow ({due_dt.strftime('%d %B %Y')})"
                d["availability_class"] = "badge-warning"
            elif days_left == 0:
                d["availability_badge"] = "Due today"
                d["availability_class"] = "badge-warning"
            else:
                d["availability_badge"] = f"Overdue by {abs(days_left)} days"
                d["availability_class"] = "badge-danger"
        except Exception:
            d["availability_badge"] = f"Expected return: {exp}"
            d["availability_class"] = "badge-warning"
    else:
        d["days_left"] = None
        d["is_overdue"] = False
        d["availability_badge"] = "Available in Library (Ready to borrow)"
        d["availability_class"] = "badge-success"

    history = conn.execute("""
        SELECT t.issue_date, t.issue_time, t.due_date, t.return_date, t.return_time, t.status
        FROM transactions t
        WHERE t.book_id = ?
        ORDER BY t.id DESC
        LIMIT 10
    """, (book_id,)).fetchall()

    conn.close()
    return {"book": d, "history": [dict(h) for h in history]}


def get_patron_loans_by_identifier(identifier):
    """Lookup active loans for a student or teacher using Register Number or Barcode"""
    p_dict = get_patron_by_barcode(identifier)
    if not p_dict:
        return None, []

    conn = get_connection()
    loans = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               b.authors as book_authors, b.account_number as book_account_number
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.patron_id = ? AND t.status = 'issued'
        ORDER BY t.due_date ASC
    """, (p_dict["id"],)).fetchall()

    today = datetime.now().date()
    fine_val = conn.execute("SELECT value FROM settings WHERE key='fine_per_day'").fetchone()
    fine_rate = float(fine_val["value"]) if fine_val else 2.0
    conn.close()

    loan_list = []
    for l in loans:
        ld = dict(l)
        due_dt = datetime.strptime(ld["due_date"], "%Y-%m-%d").date()
        diff = (due_dt - today).days
        ld["days_left"] = diff
        ld["is_overdue"] = diff < 0
        if diff < 0:
            overdue_days = abs(diff)
            ld["calculated_fine"] = overdue_days * fine_rate
            ld["status_label"] = f"Overdue by {overdue_days} days"
            ld["status_class"] = "badge-danger"
        elif diff == 0:
            ld["calculated_fine"] = 0.0
            ld["status_label"] = "Due today"
            ld["status_class"] = "badge-warning"
        else:
            ld["calculated_fine"] = 0.0
            ld["status_label"] = f"{diff} days left"
            ld["status_class"] = "badge-info"
        loan_list.append(ld)

    return p_dict, loan_list


def check_patron_no_due_status(identifier):
    """
    Checks if a patron (student or faculty) has any pending dues (unreturned books or unpaid fines).
    Returns complete breakdown suitable for No-Due Certificate verification.
    """
    p_dict = get_patron_by_barcode(identifier)
    if not p_dict:
        return {"found": False, "message": f"No student or staff found matching '{identifier}'"}

    conn = get_connection()
    today = datetime.now().date()
    fine_val = conn.execute("SELECT value FROM settings WHERE key='fine_per_day'").fetchone()
    fine_rate = float(fine_val["value"]) if fine_val else 2.0

    # 1. Active issued books
    active_rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode,
               b.authors as book_authors, b.account_number as book_acc
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.patron_id = ? AND t.status = 'issued'
        ORDER BY t.due_date ASC
    """, (p_dict["id"],)).fetchall()

    active_loans = []
    total_active_fines = 0.0
    for r in active_rows:
        ld = dict(r)
        due_dt = datetime.strptime(ld["due_date"], "%Y-%m-%d").date()
        diff = (due_dt - today).days
        ld["days_left"] = diff
        ld["is_overdue"] = diff < 0
        if diff < 0:
            overdue_days = abs(diff)
            calc_fine = overdue_days * fine_rate
            ld["calculated_fine"] = calc_fine
            total_active_fines += calc_fine
            ld["status_label"] = f"Overdue by {overdue_days} days"
            ld["status_class"] = "badge-danger"
        elif diff == 0:
            ld["calculated_fine"] = 0.0
            ld["status_label"] = "Due today"
            ld["status_class"] = "badge-warning"
        else:
            ld["calculated_fine"] = 0.0
            ld["status_label"] = f"{diff} days remaining"
            ld["status_class"] = "badge-info"
        active_loans.append(ld)

    # 2. Unpaid fines from past returned transactions
    unpaid_rows = conn.execute("""
        SELECT t.*, b.title as book_title, b.barcode as book_barcode
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.patron_id = ? AND t.status = 'returned' AND t.fine_paid = 0 AND t.fine_amount > 0
        ORDER BY t.return_date DESC
    """, (p_dict["id"],)).fetchall()

    unpaid_fines_list = [dict(r) for r in unpaid_rows]
    total_unpaid_returned_fines = sum(float(r.get("fine_amount") or 0) for r in unpaid_fines_list)

    total_pending_fines = total_active_fines + total_unpaid_returned_fines
    has_due = (len(active_loans) > 0 or total_pending_fines > 0)

    # Lifetime borrows count
    lifetime_count = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE patron_id = ?", (p_dict["id"],)
    ).fetchone()[0]

    conn.close()

    cert_id = f"SRM/EEE-LIB/NDC/{datetime.now().year}/{p_dict['id']:04d}"

    return {
        "found": True,
        "patron": p_dict,
        "has_due": has_due,
        "can_generate": not has_due,
        "active_loans": active_loans,
        "active_loans_count": len(active_loans),
        "unpaid_fines_list": unpaid_fines_list,
        "total_pending_fines": round(total_pending_fines, 2),
        "lifetime_borrows": lifetime_count,
        "certificate_id": cert_id,
        "issue_date": datetime.now().strftime("%d-%m-%Y"),
        "issue_date_long": datetime.now().strftime("%d %B %Y")
    }


def mark_patron_no_due_emailed(patron_id: int, cert_id: str = "", email: str = "", success: bool = True, err_msg: str = ""):
    """Record that a patron has received their No Due Certificate email."""
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if success:
        c.execute("UPDATE patrons SET no_due_emailed_at = ? WHERE id = ?", (now_str, patron_id))
    try:
        c.execute(
            "INSERT INTO no_due_dispatches (patron_id, cert_id, sent_to_email, sent_at, status, error_message) VALUES (?, ?, ?, ?, ?, ?)",
            (patron_id, cert_id or "", email or "", now_str, "sent" if success else "failed", err_msg or "")
        )
    except Exception:
        pass
    conn.commit()
    conn.close()


def reset_all_no_due_email_status():
    """Reset the emailed status of all patrons so a new batch/term can be emailed."""
    conn = get_connection()
    conn.execute("UPDATE patrons SET no_due_emailed_at = NULL")
    conn.commit()
    conn.close()


def get_all_cleared_patrons(patron_type=None, only_unemailed=False):
    """
    Retrieve all patrons (students and teachers) who have zero pending dues
    (no active issued books and no unpaid fines from returned transactions).
    Optionally filter by patron_type: 'student', 'teacher', or None for all.
    Optionally filter only_unemailed: only patrons who haven't yet been emailed their certificate.
    """
    conn = get_connection()
    sql = """
        SELECT p.id, p.name, p.register_number, p.patron_type, p.email, p.parent_email,
               p.year, p.section, p.barcode, p.no_due_emailed_at
        FROM patrons p
        WHERE NOT EXISTS (
            SELECT 1 FROM transactions t WHERE t.patron_id = p.id AND t.status = 'issued'
        )
        AND NOT EXISTS (
            SELECT 1 FROM transactions t WHERE t.patron_id = p.id AND t.status = 'returned' AND t.fine_paid = 0 AND t.fine_amount > 0
        )
    """
    params = []
    if patron_type == "student":
        sql += " AND p.patron_type = 'student'"
    elif patron_type in ("teacher", "faculty", "staff"):
        sql += " AND p.patron_type IN ('teacher', 'faculty', 'staff')"

    if only_unemailed:
        sql += " AND (p.no_due_emailed_at IS NULL OR p.no_due_emailed_at = '')"

    sql += " ORDER BY p.patron_type DESC, p.name ASC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_no_due_bulk_summary():
    """Summary of cleared vs due patrons for bulk No Due certificate emailing, including sent tracking."""
    conn = get_connection()
    total_patrons = conn.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]

    cleared_sql = """
        SELECT p.id, p.patron_type, p.email, p.parent_email, p.no_due_emailed_at
        FROM patrons p
        WHERE NOT EXISTS (
            SELECT 1 FROM transactions t WHERE t.patron_id = p.id AND t.status = 'issued'
        )
        AND NOT EXISTS (
            SELECT 1 FROM transactions t WHERE t.patron_id = p.id AND t.status = 'returned' AND t.fine_paid = 0 AND t.fine_amount > 0
        )
    """
    cleared_rows = conn.execute(cleared_sql).fetchall()
    conn.close()

    cleared_total = len(cleared_rows)
    cleared_with_email = sum(1 for r in cleared_rows if (r["email"] or r["parent_email"]))
    already_emailed = sum(1 for r in cleared_rows if (r["email"] or r["parent_email"]) and r["no_due_emailed_at"])
    pending_to_email = cleared_with_email - already_emailed
    students_cleared = sum(1 for r in cleared_rows if r["patron_type"] == "student")
    teachers_cleared = sum(1 for r in cleared_rows if r["patron_type"] in ("teacher", "faculty", "staff"))
    has_due_count = total_patrons - cleared_total

    return {
        "total_patrons": total_patrons,
        "cleared_total": cleared_total,
        "cleared_with_email": cleared_with_email,
        "already_emailed": already_emailed,
        "pending_to_email": pending_to_email,
        "students_cleared": students_cleared,
        "teachers_cleared": teachers_cleared,
        "has_due_count": has_due_count
    }




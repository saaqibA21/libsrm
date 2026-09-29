"""
SRM EEE Library Management System - Database Layer
SQLite-based storage for books, patrons, transactions, settings
"""

import sqlite3
import os
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

    # Transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            patron_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine_amount REAL DEFAULT 0.0,
            fine_paid INTEGER DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'issued',
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (patron_id) REFERENCES patrons(id)
        )
    """)

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


# ─── Books ─────────────────────────────────────────────────────────────────────

def add_book(barcode, title, publisher="", authors="", edition="", account_number=""):
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
    return dict(row) if row else None


def get_book_by_id(book_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


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
    return [dict(r) for r in rows]


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
    return [dict(r) for r in rows]


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
    if not barcode:
        clean_reg = (register_number or "").strip().replace(" ", "").replace("/", "")
        prefix = "ST" if patron_type == "student" else "TC"
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
    Handles case-insensitivity, spaces, and 'ST'/'TC' prefix variations.
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

    # 2. Try prefix variations (e.g. user entered reg no without ST/TC, or with ST/TC)
    if not row:
        stripped_prefix = clean[2:] if clean.upper().startswith(("ST", "TC")) else clean
        row = conn.execute("""
            SELECT * FROM patrons
            WHERE UPPER(barcode) = UPPER(?)
               OR UPPER(barcode) = UPPER(?)
               OR UPPER(register_number) = UPPER(?)
               OR UPPER(register_number) = UPPER(?)
        """, (
            f"ST{clean}",
            f"TC{clean}",
            stripped_prefix,
            clean
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
            CASE patron_type WHEN 'student' THEN 1 ELSE 2 END,
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
    students = conn.execute("SELECT COUNT(*) FROM patrons WHERE patron_type='student'").fetchone()[0]
    teachers = conn.execute("SELECT COUNT(*) FROM patrons WHERE patron_type='teacher'").fetchone()[0]
    conn.close()
    return {"total": total, "students": students, "teachers": teachers}


# ─── Transactions ──────────────────────────────────────────────────────────────

def issue_book(book_id, patron_id, patron_type="student", issue_date=None, due_date=None):
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

        loan_key = "loan_period_teacher" if patron_type == "teacher" else "loan_period_student"
        loan_days = int(conn.execute("SELECT value FROM settings WHERE key=?", (loan_key,)).fetchone()["value"])

        if not issue_date:
            issue_date = datetime.now().strftime("%Y-%m-%d")

        if not due_date:
            try:
                base_dt = datetime.strptime(issue_date, "%Y-%m-%d")
            except Exception:
                base_dt = datetime.now()
            due_date = (base_dt + timedelta(days=loan_days)).strftime("%Y-%m-%d")

        conn.execute("""
            INSERT INTO transactions (book_id, patron_id, issue_date, due_date, status)
            VALUES (?,?,?,?,'issued')
        """, (book_id, patron_id, issue_date, due_date))

        conn.execute("UPDATE books SET status='issued' WHERE id=?", (book_id,))
        conn.commit()
        return True, f"Book issued successfully. Due date: {due_date}"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def return_book(transaction_id, return_date=None):
    conn = get_connection()
    try:
        txn = conn.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not txn:
            return False, "Transaction not found"
        if txn["status"] == "returned":
            return False, "Book already returned"

        if not return_date:
            return_date = datetime.now().strftime("%Y-%m-%d")

        try:
            ret_date_obj = datetime.strptime(return_date, "%Y-%m-%d")
        except Exception:
            ret_date_obj = datetime.now()
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
            UPDATE transactions SET return_date=?, fine_amount=?, status='returned'
            WHERE id=?
        """, (return_date, fine, transaction_id))

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
        SELECT t.*, b.title as book_title, b.barcode as book_barcode
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        WHERE t.patron_id=?
        ORDER BY t.id DESC
    """, (patron_id,)).fetchall()
    conn.close()
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
    today = datetime.now().strftime("%Y-%m-%d")

    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = conn.execute("SELECT COUNT(*) FROM books WHERE status='available'").fetchone()[0]
    issued_books = conn.execute("SELECT COUNT(*) FROM books WHERE status='issued'").fetchone()[0]
    total_patrons = conn.execute("SELECT COUNT(*) FROM patrons").fetchone()[0]
    overdue = conn.execute("SELECT COUNT(*) FROM transactions WHERE status='issued' AND due_date < ?", (today,)).fetchone()[0]
    issued_today = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(issue_date)=date('now','localtime')").fetchone()[0]
    returned_today = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(return_date)=date('now','localtime')").fetchone()[0]
    total_fines = conn.execute("SELECT COALESCE(SUM(fine_amount),0) FROM transactions WHERE fine_paid=0 AND status='returned'").fetchone()[0]

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
    """Search how many times each book has been borrowed and its circulation status."""
    conn = get_connection()
    q = f"%{query}%"
    sql = """
        SELECT b.id, b.title, b.authors, b.barcode, b.account_number, b.status,
               COUNT(t.id) as times_borrowed,
               MAX(t.issue_date) as last_issued_date,
               (SELECT p.name FROM transactions t2 JOIN patrons p ON t2.patron_id = p.id 
                WHERE t2.book_id = b.id AND t2.status = 'issued' LIMIT 1) as current_borrower,
               (SELECT t2.due_date FROM transactions t2 
                WHERE t2.book_id = b.id AND t2.status = 'issued' LIMIT 1) as current_due_date
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


def search_patron_borrow_stats(query="", limit=50):
    """Search how many books each patron has taken, with active loans and fines."""
    conn = get_connection()
    q = f"%{query}%"
    today = datetime.now().strftime("%Y-%m-%d")
    sql = """
        SELECT p.id, p.name, p.register_number, p.patron_type, p.year, p.section, p.barcode, p.email,
               COUNT(t.id) as total_books_taken,
               SUM(CASE WHEN t.status = 'issued' THEN 1 ELSE 0 END) as active_loans_count,
               SUM(CASE WHEN t.status = 'issued' AND t.due_date < ? THEN 1 ELSE 0 END) as overdue_count,
               SUM(CASE WHEN t.fine_paid = 0 THEN t.fine_amount ELSE 0 END) as pending_fines,
               MAX(t.issue_date) as last_borrowed_date
        FROM patrons p
        LEFT JOIN transactions t ON p.id = t.patron_id
        WHERE (p.name LIKE ? OR p.register_number LIKE ? OR p.barcode LIKE ? OR p.email LIKE ?)
        GROUP BY p.id
        ORDER BY total_books_taken DESC, p.name ASC
        LIMIT ?
    """
    rows = conn.execute(sql, (today, q, q, q, q, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
        results.append(d)
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

    d = dict(book)
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
        SELECT t.issue_date, t.due_date, t.return_date, t.status
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


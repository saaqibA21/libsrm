"""
SRM EEE Library Management System — Complete Public & Librarian Web Application
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session
from datetime import datetime, timedelta
import io
import socket

from library_app.database import (
    initialize_db, get_setting, set_setting, get_all_settings,
    add_book, update_book, delete_book, get_book_by_barcode, get_book_by_id,
    search_books, get_all_books, count_books,
    search_books_with_availability, count_search_books, get_book_with_full_details,
    add_patron, update_patron, delete_patron, get_patron_by_barcode,
    get_patron_by_id, search_patrons, get_all_patrons, count_patrons,
    get_patron_loans_by_identifier,
    issue_book, return_book, get_active_transaction_by_book,
    get_patron_active_books, get_all_active_transactions,
    get_overdue_transactions, get_transaction_history, get_patron_history,
    get_dashboard_stats, get_most_borrowed_books, get_most_active_patrons,
    mark_fine_paid
)
from library_app.utils.excel_importer import (
    import_books_from_excel, import_students_from_excel, import_staff_from_excel
)

app = Flask(__name__)
app.secret_key = "srm-eee-library-secure-key-2026"

initialize_db()


def get_lan_ip():
    """Get the primary local IPv4 address for network access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.context_processor
def inject_global_vars():
    """Inject useful variables into all templates."""
    counts = count_books()
    lan_ip = get_lan_ip()
    is_staff = session.get("is_staff", False)
    lib_name = get_setting("library_name", "SRM EEE Department Library")
    return {
        "global_counts": counts,
        "lan_ip": lan_ip,
        "is_staff": is_staff,
        "lib_name": lib_name,
        "now_year": datetime.now().year,
    }


# ─── Public Portal: Catalog & Availability ─────────────────────────────────────

@app.route("/")
def public_catalog():
    """Public homepage — search catalog with live availability and expected return dates."""
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    page = int(request.args.get("page", 1))
    per_page = 30
    offset = (page - 1) * per_page

    books = search_books_with_availability(query=q, status_filter=status if status else None, limit=per_page, offset=offset)
    total_matches = count_search_books(query=q, status_filter=status if status else None)
    total_pages = max(1, (total_matches + per_page - 1) // per_page)
    counts = count_books()

    return render_template(
        "catalog.html",
        books=books,
        counts=counts,
        q=q,
        status=status,
        page=page,
        total_pages=total_pages,
        total_matches=total_matches,
    )


@app.route("/api/public/book/<int:book_id>")
def api_public_book_details(book_id):
    """API for public book modal with availability and circulation notes."""
    res = get_book_with_full_details(book_id)
    if not res:
        return jsonify({"found": False, "message": "Book not found"}), 404
    # Clean borrower details for student privacy in public API
    if "book" in res and res["book"].get("borrower_name"):
        res["book"]["borrower_name"] = "Registered Student/Faculty"
        res["book"]["borrower_reg"] = "••••••••"
    return jsonify({"found": True, **res})


# ─── Public Portal: Student My Books ───────────────────────────────────────────

@app.route("/my-books")
def my_books_page():
    """Student/Patron portal to check borrowed books and due dates."""
    reg = request.args.get("reg", "").strip()
    patron = None
    loans = []
    searched = bool(reg)

    if reg:
        patron, loans = get_patron_loans_by_identifier(reg)

    return render_template("my_books.html", patron=patron, loans=loans, reg=reg, searched=searched)


@app.route("/api/my-loans/<identifier>")
def api_my_loans(identifier):
    """API to lookup loans for a student/teacher."""
    patron, loans = get_patron_loans_by_identifier(identifier)
    if not patron:
        return jsonify({"found": False, "message": f"No patron found with ID or Barcode: {identifier}"})
    return jsonify({"found": True, "patron": patron, "loans": loans})


@app.route("/info")
def library_info():
    """Library rules, loan policy, timings, and contact."""
    settings = get_all_settings()
    return render_template("info.html", settings=settings)


# ─── Staff / Librarian Authentication ──────────────────────────────────────────

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    """Simple PIN authentication for librarian desk."""
    stored_pin = get_setting("staff_pin", "1234")
    if request.method == "POST":
        pin = request.form.get("pin", "").strip()
        if pin == stored_pin:
            session["is_staff"] = True
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        return render_template("staff_login.html", error="Incorrect PIN. Please try again.")

    if session.get("is_staff"):
        return redirect(url_for("dashboard"))
    return render_template("staff_login.html")


@app.route("/staff/logout")
def staff_logout():
    """Logout of staff desk mode."""
    session.pop("is_staff", None)
    return redirect(url_for("public_catalog"))


def require_staff():
    """Helper to check staff session."""
    return session.get("is_staff", False)


# ─── Librarian Desk: Dashboard ─────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    stats = get_dashboard_stats()
    overdue = get_overdue_transactions()[:10]
    recent = get_transaction_history(limit=10)
    return render_template("dashboard.html", stats=stats, overdue=overdue, recent=recent)


@app.route("/api/stats")
def api_stats():
    return jsonify(get_dashboard_stats())


# ─── Librarian Desk: Issue / Return ────────────────────────────────────────────

@app.route("/issue")
def issue_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    return render_template("issue.html")


@app.route("/return")
def return_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    return render_template("return.html")


@app.route("/api/scan/book/<barcode>")
def scan_book(barcode):
    book = get_book_by_barcode(barcode.strip())
    if not book:
        return jsonify({"found": False, "message": f"Book '{barcode}' not found in database"})
    txn = get_active_transaction_by_book(book["id"]) if book["status"] == "issued" else None
    return jsonify({"found": True, "book": book, "active_transaction": txn})


@app.route("/api/scan/patron/<barcode>")
def scan_patron(barcode):
    patron = get_patron_by_barcode(barcode.strip())
    if not patron:
        return jsonify({"found": False, "message": f"Patron '{barcode}' not found"})
    active_books = get_patron_active_books(patron["id"])
    today = datetime.now().strftime("%Y-%m-%d")
    for b in active_books:
        b["overdue"] = b["due_date"] < today
    return jsonify({"found": True, "patron": patron, "active_books": active_books})


@app.route("/api/issue", methods=["POST"])
def api_issue():
    if not require_staff():
        return jsonify({"success": False, "message": "Staff login required"}), 403
    data = request.json
    book_id = data.get("book_id")
    patron_id = data.get("patron_id")
    patron_type = data.get("patron_type", "student")
    success, msg = issue_book(book_id, patron_id, patron_type)
    return jsonify({"success": success, "message": msg})


@app.route("/api/return", methods=["POST"])
def api_return():
    if not require_staff():
        return jsonify({"success": False, "message": "Staff login required"}), 403
    data = request.json
    transaction_id = data.get("transaction_id")
    success, result = return_book(transaction_id)
    if success:
        fine = float(result)
        return jsonify({
            "success": True,
            "fine": fine,
            "message": f"Returned! Fine: ₹{fine:.2f}" if fine > 0 else "Returned on time — no fine!"
        })
    return jsonify({"success": False, "message": str(result)})


# ─── Librarian Desk: Books Management ──────────────────────────────────────────

@app.route("/books")
def books_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    books = search_books(q, status if status else None)
    counts = count_books()
    return render_template("books.html", books=books, counts=counts, q=q, status=status)


@app.route("/books/add", methods=["POST"])
def add_book_route():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    d = request.form
    success, msg = add_book(
        barcode=d.get("barcode", "").strip(),
        title=d.get("title", "").strip(),
        publisher=d.get("publisher", "").strip(),
        authors=d.get("authors", "").strip(),
        edition=d.get("edition", "").strip(),
        account_number=d.get("account_number", "").strip(),
    )
    return jsonify({"success": success, "message": msg})


@app.route("/books/edit/<int:book_id>", methods=["POST"])
def edit_book_route(book_id):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    d = request.form
    update_book(book_id, d.get("title"), d.get("publisher"),
                d.get("authors"), d.get("edition"), d.get("account_number"))
    return jsonify({"success": True, "message": "Book updated"})


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book_route(book_id):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    book = get_book_by_id(book_id)
    if book and book["status"] == "issued":
        return jsonify({"success": False, "message": "Cannot delete a currently issued book"})
    delete_book(book_id)
    return jsonify({"success": True, "message": "Book deleted"})


@app.route("/books/get/<int:book_id>")
def get_book_route(book_id):
    book = get_book_by_id(book_id)
    return jsonify(book or {})


@app.route("/books/import", methods=["POST"])
def import_books_route():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    f = request.files.get("file")
    if not f:
        return jsonify({"success": False, "message": "No file uploaded"})
    tmp = os.path.join(os.path.dirname(__file__), "_tmp_import.xlsx")
    f.save(tmp)
    books, errors = import_books_from_excel(tmp)
    if os.path.exists(tmp): os.remove(tmp)
    added = skipped = 0
    for book in books:
        ok, _ = add_book(**book)
        if ok: added += 1
        else: skipped += 1
    return jsonify({"success": True, "added": added, "skipped": skipped, "total": len(books)})


@app.route("/books/barcodes")
def books_barcodes():
    base = os.path.dirname(os.path.dirname(__file__))
    master_pdf = os.path.join(base, "ALL_BOOKS_BARCODES.pdf")
    if os.path.exists(master_pdf):
        return send_file(master_pdf, as_attachment=True, download_name="ALL_BOOKS_BARCODES.pdf", mimetype="application/pdf")
    from library_app.utils.barcode_utils import generate_barcode_pdf
    books = get_all_books()
    items = [{"barcode": b["barcode"], "name": b["title"][:45],
              "extra": f"Acc: {b.get('account_number','')} | {(b.get('authors','') or '')[:30]}"} for b in books]
    generate_barcode_pdf(items, master_pdf, "book")
    return send_file(master_pdf, as_attachment=True, download_name="ALL_BOOKS_BARCODES.pdf", mimetype="application/pdf")


# ─── Librarian Desk: Patrons Management ────────────────────────────────────────

@app.route("/patrons")
def patrons_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    q = request.args.get("q", "")
    ptype = request.args.get("type", "")
    patrons = search_patrons(q, ptype if ptype else None)
    counts = count_patrons()
    return render_template("patrons.html", patrons=patrons, counts=counts, q=q, ptype=ptype)


@app.route("/patrons/add", methods=["POST"])
def add_patron_route():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    d = request.form
    success, msg = add_patron(
        barcode=d.get("barcode","").strip(),
        register_number=d.get("register_number","").strip(),
        name=d.get("name","").strip(),
        patron_type=d.get("patron_type","student"),
        year=d.get("year",""),
        section=d.get("section","").strip(),
        mobile=d.get("mobile","").strip(),
        email=d.get("email","").strip(),
        parent_mobile=d.get("parent_mobile","").strip(),
        parent_email=d.get("parent_email","").strip(),
    )
    return jsonify({"success": success, "message": msg})


@app.route("/patrons/edit/<int:pid>", methods=["POST"])
def edit_patron_route(pid):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    d = request.form
    update_patron(pid, d.get("name"), d.get("patron_type"), d.get("year"),
                  d.get("section"), d.get("mobile"), d.get("email"),
                  d.get("parent_mobile"), d.get("parent_email"))
    return jsonify({"success": True, "message": "Patron updated"})


@app.route("/patrons/delete/<int:pid>", methods=["POST"])
def delete_patron_route(pid):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    delete_patron(pid)
    return jsonify({"success": True})


@app.route("/patrons/get/<int:pid>")
def get_patron_route(pid):
    p = get_patron_by_id(pid)
    return jsonify(p or {})


@app.route("/patrons/history/<int:pid>")
def patron_history(pid):
    patron = get_patron_by_id(pid)
    history = get_patron_history(pid)
    return jsonify({"patron": patron, "history": history})


@app.route("/patrons/import/students", methods=["POST"])
def import_students_route():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    f = request.files.get("file")
    year = request.form.get("year", "I")
    section = request.form.get("section", "A")
    if not f:
        return jsonify({"success": False, "message": "No file uploaded"})
    tmp = os.path.join(os.path.dirname(__file__), "_tmp_students.xlsx")
    f.save(tmp)
    patrons, errors = import_students_from_excel(tmp, year, section)
    if os.path.exists(tmp): os.remove(tmp)
    added = skipped = 0
    for p in patrons:
        ok, _ = add_patron(**p)
        if ok: added += 1
        else: skipped += 1
    return jsonify({"success": True, "added": added, "skipped": skipped})


@app.route("/patrons/import/staff", methods=["POST"])
def import_staff_route():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    f = request.files.get("file")
    if not f:
        return jsonify({"success": False, "message": "No file uploaded"})
    ext = f.filename.rsplit(".", 1)[-1].lower()
    tmp = os.path.join(os.path.dirname(__file__), f"_tmp_staff.{ext}")
    f.save(tmp)
    patrons, errors = import_staff_from_excel(tmp)
    if os.path.exists(tmp): os.remove(tmp)
    added = skipped = 0
    for p in patrons:
        ok, _ = add_patron(**p)
        if ok: added += 1
        else: skipped += 1
    return jsonify({"success": True, "added": added, "skipped": skipped})


@app.route("/patrons/barcodes")
def patrons_barcodes():
    base = os.path.dirname(os.path.dirname(__file__))
    master_pdf = os.path.join(base, "ALL_PATRONS_BARCODES.pdf")
    if os.path.exists(master_pdf):
        return send_file(master_pdf, as_attachment=True, download_name="ALL_PATRONS_BARCODES.pdf", mimetype="application/pdf")
    from library_app.utils.barcode_utils import generate_barcode_pdf
    patrons = get_all_patrons()
    items = []
    for p in patrons:
        ptype = (p.get("patron_type", "") or "").title()
        reg = p.get("register_number", "") or ""
        sec = p.get("section", "") or ""
        yr = p.get("year", "") or ""
        extra_txt = f"{ptype}"
        if yr: extra_txt += f" - Yr {yr}"
        if sec: extra_txt += f" Sec {sec}"
        extra_txt += f" | {reg}"
        items.append({"barcode": p["barcode"], "name": p["name"], "extra": extra_txt})
    generate_barcode_pdf(items, master_pdf, "patron")
    return send_file(master_pdf, as_attachment=True, download_name="ALL_PATRONS_BARCODES.pdf", mimetype="application/pdf")


# ─── Librarian Desk: Reports ───────────────────────────────────────────────────

@app.route("/reports")
def reports_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    overdue = get_overdue_transactions()
    active = get_all_active_transactions()
    history = get_transaction_history(100)
    top_books = get_most_borrowed_books(10)
    top_patrons = get_most_active_patrons(10)
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    today = datetime.now()

    for txn in overdue:
        due = datetime.strptime(txn["due_date"], "%Y-%m-%d")
        txn["overdue_days"] = (today - due).days
        txn["fine"] = txn["overdue_days"] * fine_rate

    for txn in active:
        due = datetime.strptime(txn["due_date"], "%Y-%m-%d")
        txn["days_left"] = (due - today).days

    return render_template("reports.html", overdue=overdue, active=active,
                           history=history, top_books=top_books, top_patrons=top_patrons)


@app.route("/api/send_overdue_emails", methods=["POST"])
def send_overdue_emails():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.email_utils import send_email, build_overdue_email
    overdue = get_overdue_transactions()
    smtp_host = get_setting("email_host", "smtp.gmail.com")
    smtp_port = int(get_setting("email_port", "587"))
    smtp_user = get_setting("email_user", "")
    smtp_pass = get_setting("email_password", "")
    lib_name = get_setting("library_name", "SRM EEE Library")
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    if not smtp_user or not smtp_pass:
        return jsonify({"success": False, "message": "Email not configured in Settings"})
    patron_books = {}
    for txn in overdue:
        email = txn.get("patron_email", "")
        if not email: continue
        key = f"{email}|{txn.get('patron_name','')}"
        patron_books.setdefault(key, []).append(txn)
    sent = failed = 0
    for key, books in patron_books.items():
        email, name = key.split("|", 1)
        body = build_overdue_email(name, books, fine_rate, lib_name)
        ok, _ = send_email(email, f"[{lib_name}] Overdue Notice", body,
                           smtp_host, smtp_port, smtp_user, smtp_pass)
        if ok: sent += 1
        else: failed += 1
    return jsonify({"success": True, "sent": sent, "failed": failed})


@app.route("/api/mark_fine_paid/<int:txn_id>", methods=["POST"])
def api_mark_fine_paid(txn_id):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    mark_fine_paid(txn_id)
    return jsonify({"success": True})


# ─── Librarian Desk: Settings ──────────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    if request.method == "POST":
        for key, val in request.form.items():
            set_setting(key, val)
        return jsonify({"success": True, "message": "Settings saved successfully!"})
    s = get_all_settings()
    return render_template("settings.html", settings=s)


@app.route("/api/test_email", methods=["POST"])
def test_email():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.email_utils import send_email
    d = request.json
    ok, err = send_email(
        to_addr=d.get("email_user",""),
        subject="[SRM Library] Test Email ✅",
        body_html="<h2>✅ Email working!</h2><p>Your SRM Library email config is correct.</p>",
        smtp_host=d.get("email_host","smtp.gmail.com"),
        smtp_port=int(d.get("email_port",587)),
        smtp_user=d.get("email_user",""),
        smtp_password=d.get("email_password",""),
    )
    return jsonify({"success": ok, "message": "Test email sent!" if ok else err})


if __name__ == "__main__":
    # Bind to 0.0.0.0 so other laptops, phones, and tablets on the network can access it
    print("=" * 60)
    print(" SRM EEE Library Management System — Website Ready")
    print(f" • Local Access:     http://localhost:5000")
    print(f" • Network Access:   http://{get_lan_ip()}:5000")
    print("=" * 60)
    app.run(debug=False, port=5000, host="0.0.0.0")

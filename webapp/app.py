"""
SRM EEE Library Management System — Complete Public & Librarian Web Application
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, Response, send_from_directory
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
    mark_fine_paid, search_book_borrow_stats, search_patron_borrow_stats,
    search_transactions_by_date, normalize_edition, get_book_borrowers,
    check_patron_no_due_status, get_all_cleared_patrons, get_no_due_bulk_summary,
    mark_patron_no_due_emailed, reset_all_no_due_email_status
)
from library_app.utils.excel_importer import (
    import_books_from_excel, import_students_from_excel, import_staff_from_excel
)

app = Flask(__name__)
app.secret_key = "srm-eee-library-secure-key-2026"

initialize_db()


@app.template_filter("format_edition")
def format_edition_filter(val):
    return normalize_edition(val)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.ico", mimetype="image/vnd.microsoft.icon")


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
        "settings": get_all_settings(),
    }


# ─── Keep-Alive & Health Check (Prevents Render Free-Tier Sleep) ────────────────

@app.route("/healthz")
@app.route("/api/ping")
def health_check():
    """Ultra-fast, zero-overhead health endpoint for keep-alive pings."""
    return jsonify({
        "status": "healthy",
        "service": "srm-library",
        "timestamp": datetime.now().isoformat()
    }), 200


def start_keep_alive_daemon():
    """Background thread that periodically pings the Render service every 10 mins so it stays awake."""
    external_url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("APP_URL") or "https://eeelibrary.org"
    if not external_url:
        return

    import threading, urllib.request, time

    def _pinger():
        target = f"{external_url.rstrip('/')}/healthz"
        print(f"[Keep-Alive] Daemon started. Targeting: {target}")
        time.sleep(30)
        while True:
            try:
                req = urllib.request.Request(target, headers={"User-Agent": "SRM-KeepAlive-Worker/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    pass
                print(f"[Keep-Alive] Ping successfully sent to {target}")
            except Exception as e:
                print(f"[Keep-Alive] Ping notice: {e}")

            # Check and run daily 6:00 PM IST GitHub cloud backup
            try:
                from library_app.utils.github_backup import check_and_run_daily_backup
                check_and_run_daily_backup()
            except Exception as e:
                print(f"[Auto-Backup] Scheduler notice: {e}")

            # Check and run daily 6:00 PM IST automated daily report email to Dr. K. Saravanan
            try:
                from library_app.utils.daily_report_service import check_and_run_daily_report_email
                check_and_run_daily_report_email()
            except Exception as e:
                print(f"[Daily-Report] Scheduler notice: {e}")

            # Check and run daily 6:00 AM IST automated No Due certificates batch campaign
            try:
                from library_app.utils.no_due_campaign_service import check_and_run_daily_campaign
                check_and_run_daily_campaign()
            except Exception as e:
                print(f"[NoDue-AutoPilot] Scheduler notice: {e}")

            time.sleep(600)  # Ping every 10 minutes (Render sleep threshold is 15 min)

    t = threading.Thread(target=_pinger, daemon=True, name="RenderKeepAlive")
    t.start()


start_keep_alive_daemon()


# ─── Public Portal: Catalog & Availability ─────────────────────────────────────

@app.route("/")
@app.route("/catalog")
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


# ─── Librarian Desk: Dashboard & Hub ───────────────────────────────────────────

@app.route("/librarian")
def librarian_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    stats = get_dashboard_stats()
    overdue = get_overdue_transactions()[:10]
    recent = get_transaction_history(limit=10)
    return render_template("librarian.html", stats=stats, overdue=overdue, recent=recent)


@app.route("/dashboard")
def dashboard():
    return redirect(url_for("librarian_page"))


@app.route("/api/download/last_import/<import_type>")
def download_last_import(import_type):
    if not require_staff():
        return jsonify({"error": "Unauthorized"}), 403
    base = os.path.dirname(__file__)
    pdf_path = os.path.join(base, f"_last_{import_type}_barcodes.pdf")
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=f"new_{import_type}_barcodes.pdf", mimetype="application/pdf")
    return jsonify({"error": "No recent import found"}), 404


@app.route("/api/stats")
def api_stats():
    return jsonify(get_dashboard_stats())


@app.route("/api/qr/<text>")
def api_qr_image(text):
    """Serve a phone-screen-scannable 2D QR Code image with public caching."""
    from library_app.utils.barcode_utils import generate_qr_image
    img_bytes = generate_qr_image(text)
    res = send_file(io.BytesIO(img_bytes), mimetype="image/png")
    res.headers["Cache-Control"] = "public, max-age=86400"
    return res


@app.route("/api/barcode/<text>")
@app.route("/api/barcode/image/<text>")
def api_barcode_image(text):
    """Serve crisp PNG barcode image for single book/patron barcode display, phone screen, and printing."""
    from library_app.utils.barcode_utils import generate_barcode_image
    try:
        clean_code = text.strip()
        img_bytes = generate_barcode_image(clean_code)
        as_attachment = request.args.get("download") == "1"
        res = send_file(
            io.BytesIO(img_bytes),
            mimetype="image/png",
            as_attachment=as_attachment,
            download_name=f"barcode_{clean_code}.png"
        )
        if not as_attachment:
            res.headers["Cache-Control"] = "public, max-age=86400"
        return res
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


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
    data = request.json or {}
    patron_id = data.get("patron_id")
    patron_type = data.get("patron_type")
    if patron_id:
        p_obj = get_patron_by_id(patron_id)
        if p_obj:
            patron_type = p_obj.get("patron_type") or patron_type
    patron_type = patron_type or "student"

    # Support both multi-book (book_ids) and single book (book_id)
    book_ids = data.get("book_ids")
    if not book_ids:
        single_id = data.get("book_id")
        if single_id:
            book_ids = [single_id]
        else:
            return jsonify({"success": False, "message": "No books selected to issue"}), 400

    if not patron_id:
        return jsonify({"success": False, "message": "No patron selected"}), 400

    issue_date = (data.get("issue_date") or "").strip() or None
    due_date = (data.get("due_date") or "").strip() or None
    issue_time = (data.get("issue_time") or "").strip() or None

    issued_count = 0
    errors = []
    due_dates = []

    for bid in book_ids:
        success, msg = issue_book(bid, patron_id, patron_type, issue_date=issue_date, due_date=due_date, issue_time=issue_time)
        if success:
            issued_count += 1
            if "Due date:" in msg:
                due_dates.append(msg.split("Due date:")[-1].strip())
        else:
            errors.append(msg)

    if issued_count == len(book_ids):
        due_str = f" Due date: {due_dates[0]}" if due_dates else ""
        return jsonify({
            "success": True,
            "issued_count": issued_count,
            "message": f"Successfully issued {issued_count} book{'s' if issued_count > 1 else ''}!{due_str}"
        })
    elif issued_count > 0:
        return jsonify({
            "success": True,
            "issued_count": issued_count,
            "message": f"Issued {issued_count} of {len(book_ids)} books. Note: {'; '.join(errors)}"
        })
    else:
        return jsonify({
            "success": False,
            "message": errors[0] if errors else "Failed to issue books"
        })



@app.route("/api/return", methods=["POST"])
def api_return():
    if not require_staff():
        return jsonify({"success": False, "message": "Staff login required"}), 403
    data = request.json or {}
    transaction_id = data.get("transaction_id")
    return_date = (data.get("return_date") or "").strip() or None
    return_time = (data.get("return_time") or "").strip() or None
    success, result = return_book(transaction_id, return_date=return_date, return_time=return_time)
    if success:
        fine = float(result)
        time_display = f" at {return_time}" if return_time else ""
        return jsonify({
            "success": True,
            "fine": fine,
            "message": f"Returned on {return_date or 'today'}{time_display}! Fine: ₹{fine:.2f}" if fine > 0 else f"Returned on {return_date or 'today'}{time_display} — no fine!"
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
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "xlsx"
    tmp = os.path.join(os.path.dirname(__file__), f"_tmp_import.{ext}")
    f.save(tmp)
    books, errors = import_books_from_excel(tmp)
    if os.path.exists(tmp): os.remove(tmp)
    added = skipped = 0
    added_items = []
    for book in books:
        ok, _ = add_book(**book)
        if ok:
            added += 1
            added_items.append({
                "barcode": book["barcode"],
                "name": book["title"][:45],
                "extra": f"Acc: {book.get('account_number','')} | {(book.get('authors','') or '')[:30]}"
            })
        else:
            skipped += 1

    pdf_available = False
    if added_items:
        try:
            from library_app.utils.barcode_utils import generate_barcode_pdf
            batch_pdf = os.path.join(os.path.dirname(__file__), "_last_books_barcodes.pdf")
            generate_barcode_pdf(added_items, batch_pdf, "book")
            pdf_available = True
        except Exception:
            pass

    return jsonify({
        "success": True,
        "added": added,
        "skipped": skipped,
        "total": len(books),
        "pdf_download_url": "/api/download/last_import/books" if pdf_available else None,
        "sample_barcodes": [item["barcode"] for item in added_items[:5]]
    })


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

@app.route("/books/barcode_label/<int:book_id>")
def book_single_barcode_pdf(book_id):
    """Generate a single-label printable PDF for a damaged/replacement book barcode."""
    book = get_book_by_id(book_id)
    if not book:
        return "Book not found", 404
    from library_app.utils.barcode_utils import generate_barcode_pdf
    item = {
        "barcode": book["barcode"],
        "name": book["title"][:45],
        "extra": f"Acc: {book.get('account_number','')} | {(book.get('authors','') or '')[:30]}"
    }
    tmp_path = os.path.join(os.path.dirname(__file__), f"_tmp_single_book_{book_id}.pdf")
    generate_barcode_pdf([item], tmp_path, "book")
    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(tmp_path):
        try: os.remove(tmp_path)
        except Exception: pass
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Label_{book['barcode']}.pdf"
    )


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
    name = d.get("name","").strip()
    email = d.get("email","").strip()
    mobile = d.get("mobile","").strip()

    if not name:
        return jsonify({"success": False, "message": "Full Name is required"}), 400
    if not email:
        return jsonify({"success": False, "message": "Email ID is mandatory. Please provide a valid email address."}), 400
    if not mobile:
        return jsonify({"success": False, "message": "Phone / Mobile number is mandatory. Please provide a valid mobile number."}), 400

    year = d.get("year","").strip()
    patron_type = d.get("patron_type","student")
    if year.upper() == "RS" and patron_type != "teacher":
        patron_type = "research_scholar"
    if patron_type == "research_scholar" and (not year or year == "—"):
        year = "RS"

    success, msg = add_patron(
        barcode=d.get("barcode","").strip(),
        register_number=d.get("register_number","").strip(),
        name=name,
        patron_type=patron_type,
        designation=d.get("designation","").strip(),
        year=year,
        section=d.get("section","").strip(),
        mobile=mobile,
        email=email,
        parent_mobile=d.get("parent_mobile","").strip(),
        parent_email=d.get("parent_email","").strip(),
    )
    return jsonify({"success": success, "message": msg})


@app.route("/patrons/edit/<int:pid>", methods=["POST"])
def edit_patron_route(pid):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    d = request.form
    name = d.get("name","").strip()
    email = d.get("email","").strip()
    mobile = d.get("mobile","").strip()

    if not name:
        return jsonify({"success": False, "message": "Full Name is required"}), 400
    if not email:
        return jsonify({"success": False, "message": "Email ID is mandatory. Please provide a valid email address."}), 400
    if not mobile:
        return jsonify({"success": False, "message": "Phone / Mobile number is mandatory. Please provide a valid mobile number."}), 400

    year = d.get("year","").strip()
    patron_type = d.get("patron_type","student")
    if year.upper() == "RS" and patron_type != "teacher":
        patron_type = "research_scholar"
    if patron_type == "research_scholar" and (not year or year == "—"):
        year = "RS"

    update_patron(pid, name, patron_type, year,
                  d.get("section"), mobile, email,
                  d.get("parent_mobile"), d.get("parent_email"),
                  designation=d.get("designation","").strip())
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
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "xlsx"
    tmp = os.path.join(os.path.dirname(__file__), f"_tmp_students.{ext}")
    f.save(tmp)
    patrons, errors = import_students_from_excel(tmp, year, section)
    if os.path.exists(tmp): os.remove(tmp)
    added = skipped = 0
    added_items = []
    for p in patrons:
        if str(year).strip().upper() == "RS":
            p["patron_type"] = "research_scholar"
            if not p.get("designation"):
                p["designation"] = "Research Scholar"
        ok, _ = add_patron(**p)
        if ok:
            added += 1
            extra_txt = f"Research Scholar - {section} | {p.get('register_number','')}" if str(year).strip().upper() == "RS" else f"Student - Yr {year} Sec {section} | {p.get('register_number','')}"
            added_items.append({
                "barcode": p["barcode"],
                "name": p["name"],
                "extra": extra_txt
            })
        else:
            skipped += 1

    pdf_available = False
    if added_items:
        try:
            from library_app.utils.barcode_utils import generate_barcode_pdf
            batch_pdf = os.path.join(os.path.dirname(__file__), "_last_students_barcodes.pdf")
            generate_barcode_pdf(added_items, batch_pdf, "patron")
            pdf_available = True
        except Exception:
            pass

    auto_email = request.form.get("auto_email") in ["1", "true", "on"]
    emails_sent = 0
    if auto_email and added_items:
        smtp_user = get_setting("email_user", "")
        smtp_pass = get_setting("email_password", "")
        if smtp_user and smtp_pass:
            from library_app.utils.email_utils import send_patron_barcode_email
            import time
            smtp_host = get_setting("email_host", "smtp.gmail.com")
            smtp_port = int(get_setting("email_port", "465"))
            from_addr = get_setting("email_from", "")
            lib_name = get_setting("library_name", "SRM EEE Department Library")
            for p in patrons:
                if p.get("email"):
                    ok, _ = send_patron_barcode_email(
                        patron=p,
                        smtp_host=smtp_host,
                        smtp_port=smtp_port,
                        smtp_user=smtp_user,
                        smtp_password=smtp_pass,
                        from_addr=from_addr,
                        library_name=lib_name
                    )
                    if ok: emails_sent += 1
                    time.sleep(0.1)

    return jsonify({
        "success": True,
        "added": added,
        "skipped": skipped,
        "total": len(patrons),
        "year": year,
        "section": section,
        "emails_sent": emails_sent,
        "pdf_download_url": "/api/download/last_import/students" if pdf_available else None,
        "sample_barcodes": [item["barcode"] for item in added_items[:5]]
    })


@app.route("/patrons/import/staff", methods=["POST"])
def import_staff_route():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    f = request.files.get("file")
    if not f:
        return jsonify({"success": False, "message": "No file uploaded"})
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "xlsx"
    tmp = os.path.join(os.path.dirname(__file__), f"_tmp_staff.{ext}")
    f.save(tmp)
    patrons, errors = import_staff_from_excel(tmp)
    if os.path.exists(tmp): os.remove(tmp)
    added = skipped = 0
    added_items = []
    for p in patrons:
        ok, _ = add_patron(**p)
        desig_str = f" • {p['designation']}" if p.get("designation") else ""
        if ok:
            added += 1
            ptype = (p.get("patron_type", "") or "").title()
            added_items.append({
                "barcode": p["barcode"],
                "name": p["name"],
                "extra": f"{ptype}{desig_str} | {p.get('register_number','')}"
            })
        else:
            # Backfill / update designation if existing patron has one
            if p.get("designation") and p.get("register_number"):
                conn = get_connection()
                conn.execute("UPDATE patrons SET designation=? WHERE register_number=?", (p["designation"], p["register_number"]))
                conn.commit()
                conn.close()
            skipped += 1

    pdf_available = False
    if added_items:
        try:
            from library_app.utils.barcode_utils import generate_barcode_pdf
            batch_pdf = os.path.join(os.path.dirname(__file__), "_last_staff_barcodes.pdf")
            generate_barcode_pdf(added_items, batch_pdf, "patron")
            pdf_available = True
        except Exception:
            pass

    auto_email = request.form.get("auto_email") in ["1", "true", "on"]
    emails_sent = 0
    if auto_email and added_items:
        smtp_user = get_setting("email_user", "")
        smtp_pass = get_setting("email_password", "")
        if smtp_user and smtp_pass:
            from library_app.utils.email_utils import send_patron_barcode_email
            import time
            smtp_host = get_setting("email_host", "smtp.gmail.com")
            smtp_port = int(get_setting("email_port", "465"))
            from_addr = get_setting("email_from", "")
            lib_name = get_setting("library_name", "SRM EEE Department Library")
            for p in patrons:
                if p.get("email"):
                    ok, _ = send_patron_barcode_email(
                        patron=p,
                        smtp_host=smtp_host,
                        smtp_port=smtp_port,
                        smtp_user=smtp_user,
                        smtp_password=smtp_pass,
                        from_addr=from_addr,
                        library_name=lib_name
                    )
                    if ok: emails_sent += 1
                    time.sleep(0.1)

    return jsonify({
        "success": True,
        "added": added,
        "skipped": skipped,
        "total": len(patrons),
        "emails_sent": emails_sent,
        "pdf_download_url": "/api/download/last_import/staff" if pdf_available else None,
        "sample_barcodes": [item["barcode"] for item in added_items[:5]]
    })


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


@app.route("/patrons/barcode_label/<int:patron_id>")
def patron_single_barcode_pdf(patron_id):
    """Generate a single-label printable PDF for a damaged/replacement patron barcode."""
    patron = get_patron_by_id(patron_id)
    if not patron:
        return "Patron not found", 404
    from library_app.utils.barcode_utils import generate_barcode_pdf
    ptype = (patron.get("patron_type", "") or "").title()
    reg = patron.get("register_number", "") or ""
    extra_txt = f"{ptype} | {reg}"
    item = {"barcode": patron["barcode"], "name": patron["name"][:45], "extra": extra_txt}
    tmp_path = os.path.join(os.path.dirname(__file__), f"_tmp_single_patron_{patron_id}.pdf")
    generate_barcode_pdf([item], tmp_path, "patron")
    with open(tmp_path, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(tmp_path):
        try: os.remove(tmp_path)
        except Exception: pass
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"ID_Label_{patron['barcode']}.pdf"
    )


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
    book_stats = search_book_borrow_stats("", limit=50)
    patron_stats = search_patron_borrow_stats("", limit=50)
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    today = datetime.now()

    for txn in overdue:
        due = datetime.strptime(txn["due_date"], "%Y-%m-%d")
        txn["overdue_days"] = max(0, (today - due).days)
        txn["calculated_fine"] = txn["overdue_days"] * fine_rate
        txn["fine"] = 0.0 if txn.get("fine_paid") else txn["calculated_fine"]

    for txn in active:
        due = datetime.strptime(txn["due_date"], "%Y-%m-%d")
        txn["days_left"] = (due - today).days

    return render_template(
        "reports.html",
        overdue=overdue,
        active=active,
        history=history,
        top_books=top_books,
        top_patrons=top_patrons,
        book_stats=book_stats,
        patron_stats=patron_stats
    )


@app.route("/reports/pdf")
def reports_pdf():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    from library_app.utils.report_pdf import generate_circulation_report_pdf
    pdf_bytes = generate_circulation_report_pdf()
    as_attachment = request.args.get("download") == "1"
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=as_attachment,
        download_name=f"SRM_Library_Circulation_Report_{stamp}.pdf"
    )


@app.route("/api/reports/send_daily_report", methods=["POST"])
def api_reports_send_daily_report():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.daily_report_service import send_daily_report_email, get_daily_report_recipient
    d = request.json or {}
    recipient = (d.get("recipient") or "").strip() or get_daily_report_recipient()
    ok, msg = send_daily_report_email(recipient=recipient, force=True)
    if ok:
        return jsonify({"success": True, "message": msg, "recipient": recipient})
    else:
        return jsonify({"success": False, "message": msg}), 500


@app.route("/api/reports/daily_report_status", methods=["GET"])
def api_reports_daily_report_status():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.daily_report_service import get_daily_report_recipient
    return jsonify({
        "success": True,
        "recipient": get_daily_report_recipient(),
        "last_status": get_setting("daily_report_last_status", "Pending / Never run"),
        "last_sent_time": get_setting("daily_report_last_sent_time", ""),
        "last_sent_date": get_setting("daily_report_last_sent_date", ""),
        "schedule": "Automated Daily at 6:00 PM IST"
    })


@app.route("/api/reports/search_books")
def api_reports_search_books():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    q = request.args.get("q", "").strip()
    data = search_book_borrow_stats(q, limit=100)
    return jsonify({"success": True, "results": data})


@app.route("/api/reports/book_borrowers/<int:book_id>")
def api_reports_book_borrowers(book_id):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    book = get_book_by_id(book_id)
    if not book:
        return jsonify({"success": False, "message": "Book not found"}), 404
    borrowers = get_book_borrowers(book_id)
    return jsonify({"success": True, "book": book, "borrowers": borrowers})


@app.route("/api/reports/search_patrons")
def api_reports_search_patrons():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    q = request.args.get("q", "").strip()
    data = search_patron_borrow_stats(q, limit=100)
    return jsonify({"success": True, "results": data})


@app.route("/api/reports/circulation_search")
def api_reports_circulation_search():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()
    date_type = request.args.get("date_type", "issue_date").strip()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all").strip()
    limit = int(request.args.get("limit", "500"))

    txns, summary = search_transactions_by_date(
        from_date=from_date,
        to_date=to_date,
        date_type=date_type,
        query=q,
        status=status,
        limit=limit
    )
    return jsonify({
        "success": True,
        "summary": summary,
        "transactions": txns
    })


@app.route("/reports/export_csv")
def export_reports_csv():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()
    date_type = request.args.get("date_type", "issue_date").strip()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all").strip()

    txns, summary = search_transactions_by_date(
        from_date=from_date,
        to_date=to_date,
        date_type=date_type,
        query=q,
        status=status,
        limit=5000
    )

    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Transaction ID", "Patron Name", "Register/Staff No", "Patron Type",
        "Designation", "Year/Section", "Book Title", "Book Barcode", "Accession No",
        "Issue Date", "Issue Time", "Due Date", "Return Date", "Return Time", "Status", "Fine Amount (INR)", "Fine Paid"
    ])
    for t in txns:
        writer.writerow([
            t.get("id"),
            t.get("patron_name"),
            t.get("patron_reg"),
            t.get("patron_type"),
            t.get("patron_designation") or "",
            f"{t.get('patron_year') or ''} {t.get('patron_section') or ''}".strip(),
            t.get("book_title"),
            t.get("book_barcode"),
            t.get("book_acc") or "",
            t.get("issue_date"),
            t.get("issue_time") or "",
            t.get("due_date"),
            t.get("return_date") or "",
            t.get("return_time") or "",
            t.get("status"),
            f"{t.get('fine_payable', 0.0):.2f}",
            "Paid" if t.get("fine_paid") else "Unpaid"
        ])

    csv_data = output.getvalue()
    filename = f"Circulation_Report_{from_date or 'start'}_to_{to_date or 'today'}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@app.route("/api/send_overdue_emails", methods=["POST"])
def send_overdue_emails():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.email_utils import send_email, build_overdue_email
    overdue = get_overdue_transactions()
    smtp_host = get_setting("email_host", "smtp.gmail.com")
    smtp_port = int(get_setting("email_port", "465"))
    smtp_user = get_setting("email_user", "")
    smtp_pass = get_setting("email_password", "")
    lib_name = get_setting("library_name", "SRM EEE Library")
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    brevo_key = get_setting("brevo_api_key", "")
    if not brevo_key and (not smtp_user or not smtp_pass):
        return jsonify({"success": False, "message": "Email not configured in Settings. Please enter Brevo API key or Gmail App Password."})
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
    paid = 1
    if request.is_json and request.json and "paid" in request.json:
        paid = 1 if request.json["paid"] else 0
    mark_fine_paid(txn_id, paid)
    return jsonify({"success": True, "fine_paid": bool(paid)})


@app.route("/api/send_patron_barcode/<int:patron_id>", methods=["POST"])
def send_patron_barcode_single(patron_id):
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized. Please login to Librarian Desk."}), 403

    from library_app.utils.email_utils import send_patron_barcode_email
    patron = get_patron_by_id(patron_id)
    if not patron:
        return jsonify({"success": False, "message": "Patron not found"}), 404

    if not patron.get("email"):
        return jsonify({"success": False, "message": f"{patron.get('name')} does not have an email address registered."}), 400

    smtp_host = get_setting("email_host", "smtp.gmail.com")
    smtp_port = int(get_setting("email_port", "465"))
    smtp_user = get_setting("email_user", "")
    smtp_pass = get_setting("email_password", "")
    from_addr = get_setting("email_from", "")
    lib_name = get_setting("library_name", "SRM EEE Department Library")

    brevo_key = get_setting("brevo_api_key", "")

    if not brevo_key and (not smtp_user or not smtp_pass):
        return jsonify({
            "success": False,
            "message": "Email not configured! Please open Settings → Email and enter Brevo API Key or Gmail App Password."
        }), 400

    ok, err = send_patron_barcode_email(
        patron=patron,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_pass,
        from_addr=from_addr,
        library_name=lib_name
    )

    if ok:
        return jsonify({"success": True, "message": f"Official digital library barcode card sent to {patron.get('email')}!"})
    else:
        return jsonify({"success": False, "message": f"Failed to send email: {err}"})


@app.route("/api/send_batch_barcode_emails", methods=["POST"])
def send_batch_barcode_emails():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized. Please login to Librarian Desk."}), 403

    from library_app.utils.email_utils import send_patron_barcode_email
    import time

    smtp_host = get_setting("email_host", "smtp.gmail.com")
    smtp_port = int(get_setting("email_port", "465"))
    smtp_user = get_setting("email_user", "")
    smtp_pass = get_setting("email_password", "")
    from_addr = get_setting("email_from", "")
    lib_name = get_setting("library_name", "SRM EEE Department Library")
    brevo_key = get_setting("brevo_api_key", "")

    if not brevo_key and (not smtp_user or not smtp_pass):
        return jsonify({
            "success": False,
            "message": "Email not configured! Please open Settings → Email and configure Brevo API Key or Gmail App Password."
        }), 400

    payload = request.get_json(silent=True) or {}
    patron_type = payload.get("patron_type") or None
    year = payload.get("year") or None
    section = payload.get("section") or None

    all_patrons = get_all_patrons()

    target_patrons = []
    for p in all_patrons:
        if patron_type and patron_type != "all" and p.get("patron_type") != patron_type:
            continue
        if year and year != "all" and (p.get("year") or "").strip().upper() != year.strip().upper():
            continue
        if section and section != "all" and (p.get("section") or "").strip().upper() != section.strip().upper():
            continue
        target_patrons.append(p)

    sent = 0
    failed = 0
    skipped_no_email = 0
    err_msgs = []

    for p in target_patrons:
        email = (p.get("email") or "").strip()
        if not email:
            skipped_no_email += 1
            continue

        ok, err = send_patron_barcode_email(
            patron=p,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_pass,
            from_addr=from_addr,
            library_name=lib_name
        )

        if ok:
            sent += 1
        else:
            failed += 1
            if len(err_msgs) < 3:
                err_msgs.append(f"{p.get('name')}: {err}")

        time.sleep(0.1)

    msg = f"Dispatched {sent} barcode email(s)."
    if skipped_no_email > 0:
        msg += f" {skipped_no_email} patrons skipped (no email address recorded)."
    if failed > 0:
        msg += f" {failed} failed: {'; '.join(err_msgs)}"

    return jsonify({
        "success": True,
        "sent": sent,
        "failed": failed,
        "skipped_no_email": skipped_no_email,
        "total": len(target_patrons),
        "message": msg
    })


# ─── Librarian Desk: Settings ──────────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if not require_staff():
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401
        return redirect(url_for("staff_login", next=request.path))
    if request.method == "POST":
        for key, val in request.form.items():
            set_setting(key, val)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": True, "message": "Settings saved successfully!"})
        return redirect(url_for("settings_page"))
    s = get_all_settings()
    return render_template("settings.html", settings=s)


@app.route("/api/test_email", methods=["POST"])
def test_email():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.email_utils import send_email
    d = request.json or {}
    brevo_key = (d.get("brevo_api_key") or get_setting("brevo_api_key", "")).strip()
    smtp_user = (d.get("email_user") or get_setting("email_user", "")).strip()
    smtp_pass = (d.get("email_password") or get_setting("email_password", "")).strip()
    smtp_host = (d.get("email_host") or get_setting("email_host", "smtp.gmail.com")).strip()
    smtp_port = int(d.get("email_port") or get_setting("email_port", 465))
    from_addr = (d.get("brevo_sender_email") or d.get("email_from") or get_setting("brevo_sender_email", "") or get_setting("email_from", "")).strip() or smtp_user
    test_to = (d.get("test_recipient") or smtp_user).strip()

    if not brevo_key and (not smtp_user or not smtp_pass):
        return jsonify({
            "success": False,
            "message": "Please enter a Brevo API key OR Gmail address and 16-character Google App Password."
        }), 400

    if not test_to:
        return jsonify({"success": False, "message": "Please specify a test recipient email address."}), 400

    ok, err = send_email(
        to_addr=test_to,
        subject="[SRM EEE Library] Email System Test",
        body_html=f"""
        <div style="font-family:sans-serif; max-width:500px; padding:20px; border:1px solid #E2E8F0; border-radius:12px;">
          <h2 style="color:#166534; margin-top:0;">SRM Library Email System Active!</h2>
          <p>This test email was successfully dispatched to <strong>{test_to}</strong>.</p>
          <p style="font-size:13px; color:#64748B;">Delivery method: <strong>{'Brevo HTTPS REST API (Port 443)' if brevo_key else 'Google SMTP (Port ' + str(smtp_port) + ')'}</strong>.</p>
        </div>
        """,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_pass,
        from_addr=from_addr,
        brevo_api_key=brevo_key
    )
    return jsonify({
        "success": ok,
        "message": f"Test email successfully delivered to {test_to}!" if ok else f"Delivery failed: {err}"
    })


@app.route("/api/backup/database")
def download_database_backup():
    """Allows authenticated librarians to download a full live SQLite database snapshot."""
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library.db")
    if not os.path.exists(db_path):
        return jsonify({"success": False, "message": "Database file not found"}), 404
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        db_path,
        as_attachment=True,
        download_name=f"srm_library_backup_{stamp}.db",
        mimetype="application/x-sqlite3"
    )


@app.route("/api/backup/github_push", methods=["POST"])
def api_backup_github_push():
    """Trigger an immediate push of the live library.db to GitHub."""
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.github_backup import push_database_to_github, get_ist_now
    now_str = get_ist_now().strftime("%d-%b-%Y %I:%M %p IST")
    data = request.json or {}
    custom_msg = data.get("commit_message") or f"Manual Library Backup via Desk — {now_str}"
    ok, result_msg = push_database_to_github(custom_msg)
    return jsonify({
        "success": ok,
        "message": result_msg,
        "last_backup_time": get_setting("github_last_backup_time", ""),
        "last_backup_status": get_setting("github_last_backup_status", ""),
        "last_commit_sha": get_setting("github_last_commit_sha", "")
    })


@app.route("/settings/save_github", methods=["POST"])
def save_github_settings():
    """Save GitHub backup configuration."""
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    d = request.form
    token = d.get("github_backup_token", "").strip()
    repo = d.get("github_backup_repo", "").strip()
    branch = d.get("github_backup_branch", "").strip()
    if token:
        set_setting("github_backup_token", token)
    if repo:
        set_setting("github_backup_repo", repo)
    if branch:
        set_setting("github_backup_branch", branch)
    return jsonify({"success": True, "message": "GitHub backup settings saved successfully!"})


# ─── Promotional Library Poster (Printable A4) ──────────────────────────────────

@app.route("/poster")
def library_poster():
    """Interactive print-ready A4 poster with live QR code matching website theme."""
    custom_url = request.args.get("url", "").strip()
    default_url = custom_url or os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("APP_URL") or request.host_url.rstrip("/")
    return render_template("poster.html", default_url=default_url)


@app.route("/api/poster/download")
def download_poster_pdf():
    """Generates and downloads a vector-crisp A4 promotional poster PDF."""
    from library_app.utils.poster_generator import build_poster_pdf
    custom_url = request.args.get("url", "").strip()
    target_url = custom_url or os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("APP_URL") or request.host_url.rstrip("/")
    pdf_bytes = build_poster_pdf(target_url)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="srm_eee_library_poster.pdf"
    )


# ─── No Due Clearance & Certificate Management ───────────────────────────────────

@app.route("/no-due")
def no_due_page():
    if not require_staff():
        return redirect(url_for("staff_login", next=request.path))
    q = request.args.get("q", "").strip()
    return render_template("no_due.html", initial_q=q)


@app.route("/api/no_due/check", methods=["GET", "POST"])
def api_no_due_check():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    identifier = ""
    if request.is_json and request.json:
        identifier = request.json.get("identifier", "").strip()
    if not identifier:
        identifier = request.args.get("identifier", "").strip() or request.args.get("q", "").strip()
    if not identifier:
        return jsonify({"success": False, "message": "Please enter or scan a Register Number or Barcode"}), 400

    result = check_patron_no_due_status(identifier)
    return jsonify(result)


@app.route("/api/no_due/pdf/<int:patron_id>")
def api_no_due_pdf(patron_id):
    if not require_staff():
        return redirect(url_for("staff_login", next=request.full_path))
    try:
        from library_app.utils.no_due_pdf import generate_no_due_certificate_pdf
        patron = get_patron_by_id(patron_id)
        if not patron:
            return jsonify({"success": False, "message": "Patron not found"}), 404

        # Verify no dues
        due_check = check_patron_no_due_status(patron.get("register_number") or patron.get("barcode"))
        if due_check.get("has_due"):
            return jsonify({
                "success": False,
                "message": "Cannot generate No Due Certificate! Patron has active unreturned books or pending fines."
            }), 400

        cert_date = request.args.get("date", "").strip() or datetime.now().strftime("%d-%m-%Y")
        cert_id = due_check.get("certificate_id")

        pdf_bytes = generate_no_due_certificate_pdf(patron, cert_date=cert_date, cert_id=cert_id)
        as_attachment = request.args.get("download") == "1"
        filename = f"SRM_No_Due_{patron.get('register_number', 'Clearance')}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=as_attachment,
            download_name=filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"PDF generation error: {e}"}), 500


@app.route("/api/no_due/send_email", methods=["POST"])
def api_no_due_send_email():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.no_due_pdf import generate_no_due_certificate_pdf
    from library_app.utils.email_utils import send_no_due_certificate_email

    d = request.json or {}
    patron_id = d.get("patron_id")
    target_email = (d.get("recipient_email") or "").strip()

    if not patron_id:
        return jsonify({"success": False, "message": "Patron ID missing"}), 400

    patron = get_patron_by_id(patron_id)
    if not patron:
        return jsonify({"success": False, "message": "Patron not found"}), 404

    due_check = check_patron_no_due_status(patron.get("register_number") or patron.get("barcode"))
    if due_check.get("has_due"):
        return jsonify({
            "success": False,
            "message": "Cannot send No Due Certificate! Patron has active books or unpaid fines."
        }), 400

    recipient = target_email or patron.get("email") or patron.get("parent_email")
    if not recipient:
        return jsonify({"success": False, "message": "No email address found for this student. Please enter an email address."}), 400

    cert_date = d.get("date", "").strip() or datetime.now().strftime("%d-%m-%Y")
    cert_id = due_check.get("certificate_id")

    pdf_bytes = generate_no_due_certificate_pdf(patron, cert_date=cert_date, cert_id=cert_id)

    ok, err = send_no_due_certificate_email(patron, pdf_bytes, cert_id, to_email=recipient)
    if ok:
        return jsonify({
            "success": True,
            "message": f"Official No Due Certificate successfully emailed to {recipient}!"
        })
    else:
        return jsonify({"success": False, "message": f"Email delivery failed: {err}"}), 500


@app.route("/api/no_due/bulk_summary", methods=["GET"])
def api_no_due_bulk_summary():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    patron_type = request.args.get("patron_type", "all").strip().lower()
    only_unemailed = request.args.get("only_unemailed", "1").strip().lower() in ("1", "true", "yes")
    filter_type = None if patron_type in ("all", "", "both") else patron_type

    summary = get_no_due_bulk_summary()
    cleared_list = get_all_cleared_patrons(filter_type, only_unemailed=only_unemailed)

    eligible_patrons = [
        {
            "id": p["id"],
            "name": p["name"],
            "register_number": p["register_number"] or p["barcode"],
            "patron_type": p["patron_type"],
            "email": p["email"] or p["parent_email"],
            "year": p.get("year"),
            "section": p.get("section"),
            "no_due_emailed_at": p.get("no_due_emailed_at")
        }
        for p in cleared_list
        if (p.get("email") or p.get("parent_email"))
    ]

    return jsonify({
        "success": True,
        "summary": summary,
        "eligible_count": len(eligible_patrons),
        "patrons": eligible_patrons
    })


@app.route("/api/no_due/reset_bulk_status", methods=["POST"])
def api_no_due_reset_bulk_status():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    reset_all_no_due_email_status()
    return jsonify({"success": True, "message": "All patron email clearance statuses have been reset."})


@app.route("/api/no_due/campaign/status", methods=["GET"])
def api_no_due_campaign_status():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.no_due_campaign_service import get_campaign_status
    status = get_campaign_status()
    return jsonify({"success": True, "campaign": status})


@app.route("/api/no_due/campaign/start", methods=["POST"])
def api_no_due_campaign_start():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    from library_app.utils.no_due_campaign_service import start_auto_campaign, dispatch_campaign_batch, get_campaign_status
    data = request.json or {}
    daily_limit = int(data.get("daily_limit") or 280)
    cert_date = (data.get("cert_date") or "").strip() or datetime.now().strftime("%d-%m-%Y")
    patron_type = (data.get("patron_type") or "all").strip().lower()
    dispatch_today_now = bool(data.get("dispatch_today_now", True))

    start_auto_campaign(daily_limit=daily_limit, cert_date=cert_date, patron_type=patron_type)

    first_batch_res = None
    if dispatch_today_now:
        ok, sent_cnt, msg = dispatch_campaign_batch(limit=daily_limit)
        first_batch_res = {"success": ok, "sent_count": sent_cnt, "message": msg}

    updated_status = get_campaign_status()
    return jsonify({
        "success": True,
        "campaign": updated_status,
        "first_batch": first_batch_res,
        "message": "Auto-Pilot Campaign activated! Dispatches daily batches until completed."
    })


@app.route("/api/no_due/campaign/stop", methods=["POST"])
def api_no_due_campaign_stop():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.no_due_campaign_service import stop_auto_campaign
    status = stop_auto_campaign()
    return jsonify({"success": True, "campaign": status, "message": "Auto-Pilot Campaign paused."})


@app.route("/api/no_due/campaign/run_now", methods=["POST"])
def api_no_due_campaign_run_now():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    from library_app.utils.no_due_campaign_service import dispatch_campaign_batch, get_campaign_status
    ok, sent_cnt, msg = dispatch_campaign_batch()
    return jsonify({
        "success": ok,
        "sent_count": sent_cnt,
        "message": msg,
        "campaign": get_campaign_status()
    })


@app.route("/api/no_due/bulk_send_batch", methods=["POST"])
def api_no_due_bulk_send_batch():
    if not require_staff():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    from library_app.utils.no_due_pdf import generate_no_due_certificate_pdf
    from library_app.utils.email_utils import send_no_due_certificate_email

    data = request.json or {}
    patron_ids = data.get("patron_ids") or []
    cert_date = (data.get("date") or "").strip() or datetime.now().strftime("%d-%m-%Y")

    if not patron_ids:
        return jsonify({"success": False, "message": "No patron IDs provided"}), 400

    results = []
    quota_exceeded = False
    quota_error_msg = ""

    for pid in patron_ids:
        try:
            patron = get_patron_by_id(pid)
            if not patron:
                results.append({"id": pid, "success": False, "message": "Patron not found"})
                continue

            due_check = check_patron_no_due_status(patron.get("register_number") or patron.get("barcode"))
            if due_check.get("has_due"):
                results.append({
                    "id": pid,
                    "name": patron.get("name"),
                    "reg": patron.get("register_number") or patron.get("barcode"),
                    "success": False,
                    "message": "Skipped: Has active dues or fines"
                })
                continue

            recipient = patron.get("email") or patron.get("parent_email")
            if not recipient:
                results.append({
                    "id": pid,
                    "name": patron.get("name"),
                    "reg": patron.get("register_number") or patron.get("barcode"),
                    "success": False,
                    "message": "Skipped: No email on record"
                })
                continue

            cert_id = due_check.get("certificate_id")
            pdf_bytes = generate_no_due_certificate_pdf(patron, cert_date=cert_date, cert_id=cert_id)
            ok, err = send_no_due_certificate_email(patron, pdf_bytes, cert_id, to_email=recipient)

            if ok:
                mark_patron_no_due_emailed(pid, cert_id, recipient, success=True)
                results.append({
                    "id": pid,
                    "name": patron.get("name"),
                    "reg": patron.get("register_number") or patron.get("barcode"),
                    "email": recipient,
                    "success": True,
                    "message": f"Sent to {recipient}"
                })
            else:
                mark_patron_no_due_emailed(pid, cert_id, recipient, success=False, err_msg=err)
                results.append({
                    "id": pid,
                    "name": patron.get("name"),
                    "reg": patron.get("register_number") or patron.get("barcode"),
                    "email": recipient,
                    "success": False,
                    "message": f"Failed: {err}"
                })

                # Check if provider reported daily quota or rate limit exhaustion
                err_lower = str(err).lower()
                is_quota = any(q in err_lower for q in [
                    "429", "quota", "limit exceeded", "exceeded your daily", 
                    "credit", "credits", "rate limit", "too many requests", "daily limit"
                ])
                if is_quota:
                    quota_exceeded = True
                    quota_error_msg = str(err)
                    break
        except Exception as e:
            results.append({
                "id": pid,
                "success": False,
                "message": f"Error: {e}"
            })

    sent_count = sum(1 for r in results if r.get("success"))
    fail_count = len(results) - sent_count

    return jsonify({
        "success": True,
        "processed": len(results),
        "sent_count": sent_count,
        "fail_count": fail_count,
        "quota_exceeded": quota_exceeded,
        "quota_error_msg": quota_error_msg,
        "results": results
    })


if __name__ == "__main__":
    # Bind to 0.0.0.0 so other laptops, phones, and tablets on the network can access it
    print("=" * 60)
    print(" SRM EEE Library Management System — Website Ready")
    print(f" • Local Access:     http://localhost:5000")
    print(f" • Network Access:   http://{get_lan_ip()}:5000")
    print("=" * 60)
    app.run(debug=False, port=5000, host="0.0.0.0")

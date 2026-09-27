# 📚 SRM EEE Library Management System

A modern, barcode-powered library management system and live Online Public Access Catalog (OPAC) for the **Department of Electrical & Electronics Engineering, SRM Institute of Science and Technology (SRMIST), Kattankulathur**.

Built with **Python Flask**, **SQLite**, and an organic editorial **Ostra Design Aesthetic**.

---

## ✨ Features

### 🌐 1. Public Catalog & Live Availability Tracking
- **Search 2,118 Textbooks:** Search by title, author, account number, or publisher.
- **Real-Time Availability:**
  - 🟢 **Available on Shelf:** In stock and ready to borrow.
  - ⏳ **Currently Borrowed:** Shows the **exact expected return date** and countdown (e.g., *"Expected return on 15 Oct 2026 (18 days remaining)"*).
- **Circulation History:** Anonymized loan timeline for every book.

### 🎓 2. Student & Faculty Self-Check Portal (`/my-books`)
- Enter your **SRM Register Number** (e.g., `RA2611005010001`) or Employee ID.
- Instantly view all textbooks currently in your possession, issue dates, due date countdowns, and any overdue fines.

### 🔐 3. Librarian Circulation Desk
- **Barcode Issue / Checkout:** Scan book barcode + scan student ID barcode with any standard USB barcode scanner.
- **Barcode Return & Fine Calculation:** Scan book barcode; automatically calculates ₹2/day overdue fine if returned late.
- **Catalog Management:** Add, edit, or delete books; batch import from Excel.
- **Patron Management:** Manage students (across Years I, II, III, IV, Sections A–D) and faculty/scholars.
- **Printable Barcode Label Sheets:** Generates standard A4 24-label sticker sheets (Code 128) for books and ID cards with zero cutoff.
- **Automated Overdue Email Notices:** One-click SMTP email reminders for patrons with overdue books.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Flask, SQLite3, Gunicorn
- **Utilities:** `openpyxl`, `python-barcode` (Code 128), `reportlab`, `Pillow`, `xlrd`
- **Frontend:** Jinja2 templates, Vanilla CSS, Google Fonts (*Playfair Display* & *Plus Jakarta Sans*), FontAwesome 6
- **Hosting Ready:** Render, Railway, PythonAnywhere, or local network / offline

---

## 🚀 Running Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/saaqibA21/libsrm.git
   cd libsrm
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the web application:**
   ```bash
   python webapp/app.py
   ```
   Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## ☁️ Deploying to Render.com (24/7 Cloud Hosting)

1. Sign in to [Render.com](https://render.com/) with your GitHub account.
2. Click **New +** → **Web Service**.
3. Select this repository: `saaqibA21/libsrm`.
4. Render will automatically detect `render.yaml` and configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
5. Select the **Free** tier and click **Deploy Web Service**!

---

## 🔐 Staff Desk Default Credentials
- **Librarian Desk PIN:** `1234` *(configurable under Settings)*

---

## 📄 License
Internal use for SRM Institute of Science and Technology, Department of Electrical & Electronics Engineering.

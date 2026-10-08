"""
Generates an official, publication-quality Project Report PDF for the SRM EEE Library System.
Uses Times New Roman typography, official SRM IST banner branding, structured tables,
and easy-to-understand explanations with zero emojis.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image, HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Times-Italic", 9)
        self.setFillColor(colors.HexColor("#556958"))
        
        # Header rule on later pages
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, 800, 555, 800)
            self.drawString(40, 805, "SRM Institute of Science and Technology - Department of EEE Library Project Report")
        
        # Footer text & page numbering
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 45, 555, 45)
        
        footer_text = "Department of Electrical and Electronics Engineering - Official Project Documentation"
        self.drawString(40, 32, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(555, 32, page_str)
        self.restoreState()


def build_project_report_pdf(output_filename="SRM_EEE_Library_Project_Report.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Custom Times New Roman Styles
    doc_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=18,
        leading=22,
        alignment=1,
        textColor=colors.HexColor('#1C3022')
    )
    doc_subtitle = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=11,
        leading=15,
        alignment=1,
        textColor=colors.HexColor('#1E3A2F'),
        spaceBefore=3
    )
    doc_meta = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#556958'),
        spaceBefore=2
    )

    h1 = ParagraphStyle(
        'Heading1',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#1C3022'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h2 = ParagraphStyle(
        'Heading2',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#1E3A2F'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=6
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#111827'),
        spaceAfter=6
    )
    bullet = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#1F2937'),
        leftIndent=15,
        spaceAfter=3
    )

    # Table styles
    th = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.white
    )
    td = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1F2937')
    )
    td_bold = ParagraphStyle(
        'TDBold',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#111827')
    )
    td_center = ParagraphStyle(
        'TDCenter',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#1F2937')
    )

    story = []

    # 1. Official Banner Header
    logo_path = os.path.abspath('webapp/static/images/srm_report_banner.png')
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=150, height=64)
        logo_img.hAlign = 'CENTER'
        story.append(logo_img)
        story.append(Spacer(1, 4))

    story.append(Paragraph("Department of Electrical and Electronics Engineering", doc_subtitle))
    story.append(Paragraph("SRM EEE Department Library Management System", doc_title))
    story.append(Paragraph("Comprehensive Project Report and Operational Documentation", doc_meta))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1C3022'), spaceBefore=4, spaceAfter=10))

    # Section 1: Introduction and Purpose
    story.append(Paragraph("1. Project Introduction and Overview", h1))
    story.append(Paragraph(
        "A school or university library holds thousands of academic books and serves hundreds of students and faculty members every single day. "
        "In a traditional setup, borrowing a book involves manual registers: library staff write down student details by hand, record book accession numbers, "
        "manually look at calendar pages to compute return due dates, and perform mental arithmetic to calculate overdue fines. "
        "If a paper register gets misplaced, damaged, or wet, vital historical records are permanently lost.",
        body
    ))
    story.append(Paragraph(
        "The <b>SRM EEE Department Library Management System</b> is a modern, computerized software application built specifically for the Department of "
        "Electrical and Electronics Engineering at SRM Institute of Science and Technology. It replaces old paper notebooks with instant, computerized barcode scanning, "
        "an online book search catalog, automated email notifications, tamper-proof clearance certificates with live QR verification, and automated daily cloud backups.",
        body
    ))

    # Key Statistics Box Table
    kpi_th = ParagraphStyle('KTH', parent=styles['Normal'], fontName='Times-Bold', fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor('#1C3022'))
    kpi_tv = ParagraphStyle('KTV', parent=styles['Normal'], fontName='Times-Bold', fontSize=13, leading=16, alignment=1, textColor=colors.HexColor('#166534'))
    stats_data = [
        [
            Paragraph("Total Catalog Textbooks<br/><b><font size='13' color='#166534'>2,118</font></b>", kpi_th),
            Paragraph("Registered Patrons<br/><b><font size='13' color='#7E22CE'>786</font></b>", kpi_th),
            Paragraph("Checkout Time<br/><b><font size='13' color='#0E7490'>&lt; 3 Seconds</font></b>", kpi_th),
            Paragraph("Catalog Visibility<br/><b><font size='13' color='#166534'>24 / 7 Online</font></b>", kpi_th),
        ]
    ]
    t_stats = Table(stats_data, colWidths=[128, 128, 128, 131])
    t_stats.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAF6')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D1E0CE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2EBDD')),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(t_stats)
    story.append(Spacer(1, 10))

    # Section 2: The Problem Solved
    story.append(Paragraph("2. Problems Solved: Manual Register vs. Digital System", h1))
    story.append(Paragraph(
        "To appreciate the value of this software, consider the clear differences between the previous manual workflow and the new automated workflow:",
        body
    ))

    comp_table_data = [
        [Paragraph("Workflow Task", th), Paragraph("Traditional Manual Method", th), Paragraph("Smart Digital System", th)],
        [
            Paragraph("Borrowing a Book", td_bold),
            Paragraph("Handwriting student name, register number, and book title in a physical ledger. Takes 2 to 3 minutes per student.", td),
            Paragraph("Barcode scanner reads the student card and textbook in one touch. Completed in under 3 seconds.", td)
        ],
        [
            Paragraph("Finding a Book", td_bold),
            Paragraph("Walking up and down library aisles hoping the book is physically on the shelf.", td),
            Paragraph("Students search by title, author, or subject on their mobile phones or laptops with instant availability status.", td)
        ],
        [
            Paragraph("Calculating Fines", td_bold),
            Paragraph("Counting elapsed calendar days manually, multiplying by fine rate, subject to human calculation errors.", td),
            Paragraph("The computer automatically tracks overdue days and calculates fines down to the exact rupee.", td)
        ],
        [
            Paragraph("Overdue Reminders", td_bold),
            Paragraph("Library staff had to manually contact students or post paper notices on bulletin boards.", td),
            Paragraph("The system dispatches friendly, automated email notifications directly to the borrower's university inbox.", td)
        ],
        [
            Paragraph("No Due Clearance", td_bold),
            Paragraph("Long queues of students waiting outside the library office for manual register verification and physical ink stamps.", td),
            Paragraph("Instantly generates a verified digital clearance PDF with a scannable QR verification code.", td)
        ],
        [
            Paragraph("Data Security", td_bold),
            Paragraph("Paper registers are permanently vulnerable to fire, water damage, torn pages, and accidental loss.", td),
            Paragraph("The entire database is automatically snapshotted and securely pushed to GitHub Cloud every evening.", td)
        ],
    ]
    t_comp = Table(comp_table_data, colWidths=[115, 200, 200])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1C3022')),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 12))

    # Section 3: Core Features Explained Simply
    story.append(Paragraph("3. Core Features of the System", h1))
    
    story.append(Paragraph("A. Online Public Access Catalog (OPAC Search)", h2))
    story.append(Paragraph(
        "Students and professors can open the library website from anywhere on campus or at home. By entering a title, author name, "
        "or subject keyword, the search engine instantly displays matching textbooks, their shelf availability status (Available on Shelf vs. Currently Borrowed), "
        "and when borrowed items are scheduled to be returned.",
        body
    ))

    story.append(Paragraph("B. Rapid Barcode Circulation (Issue and Return)", h2))
    story.append(Paragraph(
        "Operating just like a supermarket checkout counter, every textbook and patron card has a unique barcode. "
        "When issuing a book, the librarian scans the student ID card followed by the book barcode sticker. The software verifies borrower loan eligibility, "
        "assigns standard lending periods (15 days for students, 30 days for faculty), and logs the checkout instantly. "
        "Returning a book is equally simple: scanning the book barcode marks it returned, checks for any late fines, and immediately updates its status to Available.",
        body
    ))

    story.append(Paragraph("C. Automated Fine Calculation", h2))
    story.append(Paragraph(
        "When books are returned past their due date, the system automatically counts the exact number of overdue days and multiplies them by the departmental fine rate "
        "(Rs. 2.00 per day). Librarians can mark fines as paid with a single click, keeping an accurate record of collected payments.",
        body
    ))

    story.append(Paragraph("D. Polite and Automated Email Assistant", h2))
    story.append(Paragraph(
        "Communication with students is handled through automated, friendly emails dispatched from the department's dedicated email address "
        "(srmktreeedeptlibrary@gmail.com). The system sends courtesy reminders two days prior to the due date, sends overdue notices if a book is late, "
        "and dispatches official digital barcode credentials directly to new patrons upon registration.",
        body
    ))

    story.append(Paragraph("E. Digital No Due Certificate with QR Code Verification", h2))
    story.append(Paragraph(
        "Graduating students and end-of-semester candidates require a No Due clearance before obtaining hall tickets or degrees. "
        "The system scans the student's record in real time. If all borrowed books have been returned and no fines are pending, it produces an official PDF clearance certificate. "
        "Each certificate features an embedded QR code that, when scanned by an examiner or administrative officer using a smartphone camera, opens an official online verification page "
        "confirming that the certificate is authentic and officially issued by SRM Institute of Science and Technology.",
        body
    ))

    story.append(Paragraph("F. Executive Circulation Reports in Times New Roman", h2))
    story.append(Paragraph(
        "For departmental audits, NBA accreditation, and NAAC inspections, library administrators require high-quality circulation documentation. "
        "The system generates two types of official reports styled in classical Times New Roman typography with the SRM university seal banner: "
        "<br/>1. <b>Circulation and Analytics Report (A4 Portrait):</b> Highlights active loans, overdue items, top-read textbooks, and active borrowers. "
        "<br/>2. <b>Custom Date-Wise Circulation Ledger (A4 Landscape):</b> Allows administrators to filter records across any date range and download complete transaction audit sheets in either Excel CSV or printable PDF format.",
        body
    ))

    story.append(Paragraph("G. Automated Daily Cloud Backup", h2))
    story.append(Paragraph(
        "To protect institutional data against computer crashes or disk failures, the software takes a daily snapshot of the entire database and securely commits it to a remote GitHub cloud repository every day. "
        "In the event of hardware failure, the entire library management system can be restored on a new computer in less than one minute.",
        body
    ))
    story.append(PageBreak())

    # Section 4: System Architecture
    story.append(Paragraph("4. System Architecture and Technology Stack", h1))
    story.append(Paragraph(
        "The application is engineered using clean, industry-standard open-source technologies designed for stability, speed, and low maintenance:",
        body
    ))

    tech_table_data = [
        [Paragraph("Component", th), Paragraph("Technology Used", th), Paragraph("Role and Function in the System", th)],
        [
            Paragraph("User Interface (Frontend)", td_bold),
            Paragraph("HTML5, CSS3, JavaScript", td),
            Paragraph("Provides a responsive, fast, and accessible web interface that functions on desktop monitors, tablets, and smartphones.", td)
        ],
        [
            Paragraph("Application Logic (Backend)", td_bold),
            Paragraph("Python 3.12, Flask Framework", td),
            Paragraph("Coordinates business rules, validates loan periods, computes late fines, enforces librarian authentication, and serves web requests.", td)
        ],
        [
            Paragraph("Database Storage", td_bold),
            Paragraph("SQLite 3 (library.db)", td),
            Paragraph("Stores catalog records (2,118 books), registered patrons (786 accounts), checkout transactions, and system settings securely.", td)
        ],
        [
            Paragraph("Document Engine", td_bold),
            Paragraph("ReportLab PDF Library", td),
            Paragraph("Renders vector-sharp, publication-quality printable PDF reports, barcode sheets, promotional posters, and No Due certificates.", td)
        ],
        [
            Paragraph("Email Dispatch", td_bold),
            Paragraph("SMTP SSL / Brevo API", td),
            Paragraph("Dispatches official circulation receipts, due date reminders, and overdue notices securely through official university channels.", td)
        ],
        [
            Paragraph("Cloud Hosting and Version Control", td_bold),
            Paragraph("Render Cloud Platform, Git, GitHub", td),
            Paragraph("Provides 24/7 web accessibility with continuous deployment and automated cloud database backups.", td)
        ],
    ]
    t_tech = Table(tech_table_data, colWidths=[125, 140, 250])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1C3022')),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 12))

    # Section 5: Step-by-Step User Instructions
    story.append(Paragraph("5. Step-by-Step User Operational Guides", h1))
    
    story.append(Paragraph("A. For Students and Researchers", h2))
    story.append(Paragraph("1. <b>Access the Catalog:</b> Open the library portal from any browser on phone or PC.", bullet))
    story.append(Paragraph("2. <b>Search Textbooks:</b> Enter course subjects (e.g., 'Power Electronics', 'Control Systems') to see book availability.", bullet))
    story.append(Paragraph("3. <b>Check Borrowed Books:</b> Navigate to 'My Books', enter your Register Number, and view active loans, due dates, and pending fines.", bullet))
    story.append(Paragraph("4. <b>Download No Due Slip:</b> Check graduation clearance status and obtain verified clearance certificates instantly.", bullet))

    story.append(Paragraph("B. For Library Staff and Administrators", h2))
    story.append(Paragraph("1. <b>Staff Login:</b> Access the circulation desk using the secure 4-digit staff PIN.", bullet))
    story.append(Paragraph("2. <b>Issue a Book:</b> Scan the borrower card barcode, scan the textbook barcode, and confirm checkout in under 3 seconds.", bullet))
    story.append(Paragraph("3. <b>Process Returns:</b> Scan the textbook barcode. The system verifies schedule status, calculates any fine, and marks the book Available.", bullet))
    story.append(Paragraph("4. <b>Audit and Export Reports:</b> Access Reports > Date-Wise Circulation to view circulation statistics or download official PDF ledgers.", bullet))
    story.append(Spacer(1, 10))

    # Section 6: Summary and Impact
    story.append(Paragraph("6. Project Impact and Conclusion", h1))
    story.append(Paragraph(
        "The SRM EEE Department Library Management System successfully transforms a traditional manual library into a fully digitized, modern academic resource center. "
        "By replacing paper registers with instant barcode automation, computerized record verification, polite automated notifications, and tamper-proof clearance documents, "
        "the software eliminates hundreds of hours of repetitive administrative paperwork each academic term. "
        "Most importantly, it ensures complete accountability, zero data loss, and a seamless, professional experience for both students and faculty members.",
        body
    ))
    story.append(Spacer(1, 12))

    # Institutional Signature block with Faculty In-Charge
    saravanan_img = "webapp/static/images/dr_saravanan_headshot.jpg"
    p_img = Image(saravanan_img, width=42, height=52) if os.path.exists(saravanan_img) else None

    sig_lead = Paragraph(
        "<b>Faculty In-Charge:</b><br/>"
        "<b>Dr. K. Saravanan</b><br/>"
        "Associate Professor &amp; Library In-Charge<br/>"
        "Department of Electrical and Electronics Engineering, SRMIST",
        bullet
    )
    portal_info = Paragraph(
        "<b>Institutional Project Documentation</b><br/>"
        "Department of Electrical and Electronics Engineering<br/>"
        "SRM Institute of Science and Technology, Kattankulathur, Tamil Nadu, India<br/>"
        "Official Library Portal: <i>srmktreeedeptlibrary@gmail.com</i>",
        doc_meta
    )
    if p_img:
        signoff_tbl = Table([[p_img, sig_lead, portal_info]], colWidths=[48, 230, 237])
        signoff_tbl.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(KeepTogether(signoff_tbl))
    else:
        story.append(KeepTogether(portal_info))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated {output_filename} successfully!")


if __name__ == '__main__':
    build_project_report_pdf()

"""
Circulation & Analytics PDF Report Generator for SRM EEE Library
Features Times New Roman typography, center-aligned table headers and values,
official SRM IST banner branding, and custom date-wise circulation report generation.
"""

import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

from library_app.database import (
    get_dashboard_stats, get_overdue_transactions,
    get_all_active_transactions, get_most_borrowed_books,
    get_most_active_patrons, get_setting
)


def _find_srm_logo() -> str | None:
    """Locate SRM University logo image on disk, prioritizing the official banner."""
    candidates = [
        os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "static", "images", "srm_report_banner.png")),
        os.path.normpath(os.path.join(os.getcwd(), "webapp", "static", "images", "srm_report_banner.png")),
        os.path.abspath("webapp/static/images/srm_report_banner.png"),
        os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "static", "images", "srm_logo.png")),
        os.path.normpath(os.path.join(os.getcwd(), "webapp", "static", "images", "srm_logo.png")),
        os.path.abspath("webapp/static/images/srm_logo.png"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _find_staff_photo(filename: str) -> str | None:
    """Locate staff photo image on disk."""
    candidates = [
        os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "webapp", "static", "images", filename)),
        os.path.normpath(os.path.join(os.getcwd(), "webapp", "static", "images", filename)),
        os.path.abspath(f"webapp/static/images/{filename}"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def generate_circulation_report_pdf(output_path_or_buf=None) -> bytes:
    """Generate a comprehensive editorial PDF report of library circulation and analytics in Times New Roman."""
    buf = io.BytesIO() if output_path_or_buf is None else (
        output_path_or_buf if hasattr(output_path_or_buf, 'write') else open(output_path_or_buf, 'wb')
    )

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # ── Custom Times New Roman Styles ──
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=15,
        leading=19,
        alignment=1,  # TA_CENTER
        textColor=colors.HexColor('#1C3022')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=10.5,
        leading=14,
        alignment=1,  # TA_CENTER
        textColor=colors.HexColor('#1E3A2F'),
        spaceBefore=3
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=8.5,
        leading=12,
        alignment=1,  # TA_CENTER
        textColor=colors.HexColor('#556958'),
        spaceBefore=3
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#16291C'),
        spaceBefore=12,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1F2937')
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#111827')
    )
    cell_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,  # Center aligned table titles
        textColor=colors.white
    )
    cell_header_center = ParagraphStyle(
        'TableHeaderCenter',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,  # Center aligned table titles
        textColor=colors.white
    )
    cell_danger = ParagraphStyle(
        'TableDanger',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#991B1B')
    )
    kpi_card_style = ParagraphStyle(
        'KPICardCell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#1F2937')
    )
    cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#1F2937')
    )
    cell_bold_center = ParagraphStyle(
        'TableCellBoldCenter',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#111827')
    )
    cell_danger_center = ParagraphStyle(
        'TableDangerCenter',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#991B1B')
    )

    story = []
    
    # ── Header with Centered SRM Banner Logo & Center-Justified Details ──
    lib_name = get_setting("library_name", "SRM EEE Department Library")
    today_str = datetime.now().strftime("%B %d, %Y • %I:%M %p")
    
    logo_file = _find_srm_logo()
    if logo_file and "banner" in logo_file:
        # Aspect ratio of 684 x 292 is 2.34246 -> width 155, height 66.17
        logo_flowable = Image(logo_file, width=155, height=66.17)
        logo_flowable.hAlign = 'CENTER'
        story.append(logo_flowable)
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Department of Electrical &amp; Electronics Engineering — {lib_name}", subtitle_style))
        story.append(Paragraph(f"Official Circulation &amp; Analytics Report • Generated on {today_str}", meta_style))
    elif logo_file:
        logo_flowable = Image(logo_file, width=54, height=54)
        header_content = [
            Paragraph("SRM Institute of Science & Technology", title_style),
            Paragraph(f"Department of Electrical & Electronics Engineering — {lib_name}", subtitle_style),
            Paragraph(f"Official Circulation & Analytics Report • Generated on {today_str}", meta_style),
        ]
        header_table = Table([[logo_flowable, header_content, ""]], colWidths=[60, 402, 60])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph("SRM Institute of Science & Technology", title_style))
        story.append(Paragraph(f"Department of Electrical & Electronics Engineering — {lib_name}", subtitle_style))
        story.append(Paragraph(f"Official Circulation & Analytics Report • Generated on {today_str}", meta_style))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1C3022'), spaceBefore=2, spaceAfter=10))

    # ── Summary KPI Cards ──
    stats = get_dashboard_stats()
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    
    kpi_data = [
        [
            Paragraph(f"<b>Total Catalog</b><br/><font size='14'><b>{stats['total_books']}</b></font>", kpi_card_style),
            Paragraph(f"<b>On Shelf</b><br/><font size='14' color='#166534'><b>{stats['available_books']}</b></font>", kpi_card_style),
            Paragraph(f"<b>Currently Borrowed</b><br/><font size='14' color='#0E7490'><b>{stats['issued_books']}</b></font>", kpi_card_style),
            Paragraph(f"<b>Overdue Items</b><br/><font size='14' color='#991B1B'><b>{stats['overdue']}</b></font>", kpi_card_style),
            Paragraph(f"<b>Registered Patrons</b><br/><font size='14' color='#7E22CE'><b>{stats['total_patrons']}</b></font>", kpi_card_style),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[104, 104, 104, 104, 106])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAF6')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D1E0CE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2EBDD')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 16))

    # ── Section 1: Overdue Books ──
    overdue = get_overdue_transactions()
    story.append(Paragraph(f"Overdue Borrowed Books ({len(overdue)})", section_heading))
    
    now_dt = datetime.now()
    if overdue:
        overdue_table_data = [[
            Paragraph("Borrower Name", cell_header),
            Paragraph("Reg. Number", cell_header),
            Paragraph("Book Title", cell_header),
            Paragraph("Due Date", cell_header),
            Paragraph("Days Overdue", cell_header),
            Paragraph("Accrued Fine", cell_header),
        ]]
        for txn in overdue:
            try:
                due_dt = datetime.strptime(txn["due_date"], "%Y-%m-%d")
                days_over = (now_dt - due_dt).days
                fine_val = days_over * fine_rate
            except Exception:
                days_over = 0
                fine_val = 0.0
            
            overdue_table_data.append([
                Paragraph(txn.get("patron_name",""), cell_bold),
                Paragraph(txn.get("register_number","") or "—", cell_center),
                Paragraph(txn.get("book_title","")[:40], cell_style),
                Paragraph(txn.get("due_date",""), cell_danger_center),
                Paragraph(f"{days_over} days", cell_danger_center),
                Paragraph(f"Rs. {fine_val:.2f}", cell_danger_center),
            ])
        
        t_overdue = Table(overdue_table_data, colWidths=[100, 75, 172, 65, 55, 55], repeatRows=1)
        t_overdue.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991B1B')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#FFF5F5'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FCA5A5')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_overdue)
    else:
        story.append(Paragraph("<i>No overdue books recorded. All active loans are within schedule.</i>", cell_style))
    story.append(Spacer(1, 16))

    # ── Section 2: Active Loans (On Schedule) ──
    active = get_all_active_transactions()
    story.append(Paragraph(f"Active Book Circulation ({len(active)})", section_heading))
    if active:
        active_table_data = [[
            Paragraph("Borrower Name", cell_header),
            Paragraph("Type / Class", cell_header),
            Paragraph("Book Title", cell_header),
            Paragraph("Issue Date", cell_header),
            Paragraph("Due Date", cell_header),
            Paragraph("Status", cell_header),
        ]]
        for txn in active:
            ptype = (txn.get("patron_type","") or "").title()
            yr = txn.get("year","")
            type_str = f"{ptype} Yr {yr}" if yr else ptype
            try:
                due_dt = datetime.strptime(txn["due_date"], "%Y-%m-%d")
                days_left = (due_dt - now_dt).days
                st_str = "Overdue" if days_left < 0 else (f"{days_left}d left" if days_left <= 3 else "On Time")
                st_color = cell_danger_center if days_left < 0 else cell_center
            except Exception:
                st_str = "Active"
                st_color = cell_center
            
            active_table_data.append([
                Paragraph(txn.get("patron_name",""), cell_bold),
                Paragraph(type_str, cell_center),
                Paragraph(txn.get("book_title","")[:45], cell_style),
                Paragraph(txn.get("issue_date",""), cell_center),
                Paragraph(txn.get("due_date",""), cell_center),
                Paragraph(st_str, st_color),
            ])
        
        t_active = Table(active_table_data, colWidths=[110, 70, 167, 60, 60, 55], repeatRows=1)
        t_active.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1C3022')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2EBDD')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_active)
    else:
        story.append(Paragraph("<i>No books currently on loan.</i>", cell_style))
    story.append(Spacer(1, 16))

    # ── Section 3: Most Borrowed Books ──
    top_books = get_most_borrowed_books(10)
    story.append(Paragraph("Most Borrowed Books (Circulation Frequency)", section_heading))
    if top_books:
        tb_data = [[
            Paragraph("Rank", cell_header),
            Paragraph("Book Title", cell_header),
            Paragraph("Author(s)", cell_header),
            Paragraph("Times Borrowed", cell_header),
        ]]
        for idx, b in enumerate(top_books, 1):
            tb_data.append([
                Paragraph(f"#{idx}", cell_bold_center),
                Paragraph(b.get("title",""), cell_bold),
                Paragraph(b.get("authors","") or "—", cell_style),
                Paragraph(f"<b>{b.get('borrow_count', 0)} times</b>", cell_bold_center),
            ])
        t_tb = Table(tb_data, colWidths=[35, 237, 160, 90], repeatRows=1)
        t_tb.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#23432B')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,1), (0,-1), 'CENTER'),
            ('ALIGN', (3,1), (3,-1), 'CENTER'),
        ]))
        story.append(t_tb)
    story.append(Spacer(1, 16))

    # ── Section 4: Most Active Borrowers ──
    top_patrons = get_most_active_patrons(10)
    story.append(Paragraph("Most Active Library Patrons", section_heading))
    if top_patrons:
        tp_data = [[
            Paragraph("Rank", cell_header),
            Paragraph("Member Name", cell_header),
            Paragraph("Reg. Number", cell_header),
            Paragraph("Role", cell_header),
            Paragraph("Books Taken", cell_header),
        ]]
        for idx, p in enumerate(top_patrons, 1):
            tp_data.append([
                Paragraph(f"#{idx}", cell_bold_center),
                Paragraph(p.get("name",""), cell_bold),
                Paragraph(p.get("register_number","") or "—", cell_center),
                Paragraph((p.get("patron_type","") or "").title(), cell_center),
                Paragraph(f"<b>{p.get('borrow_count', 0)} books</b>", cell_bold_center),
            ])
        t_tp = Table(tp_data, colWidths=[35, 187, 110, 90, 100], repeatRows=1)
        t_tp.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A2F')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,1), (0,-1), 'CENTER'),
            ('ALIGN', (2,1), (4,-1), 'CENTER'),
        ]))
        story.append(t_tp)

    # ── Footer ──
    story.append(Spacer(1, 16))
    footer_text = "SRMIST Kattankulathur — Department of EEE Library Management System • Confidential Institutional Report"
    story.append(Paragraph(footer_text, meta_style))

    doc.build(story)
    
    if output_path_or_buf is None:
        buf.seek(0)
        return buf.read()
    elif not hasattr(output_path_or_buf, 'write'):
        buf.close()


def generate_datewise_circulation_report_pdf(
    transactions: list[dict],
    summary: dict,
    from_date: str = "",
    to_date: str = "",
    date_type: str = "issue_date",
    status: str = "all",
    query: str = "",
    output_path_or_buf=None
) -> bytes:
    """
    Generate an A4 Landscape official ledger report of custom date-filtered circulation records.
    Styled in Times New Roman with centered table titles, numeric columns, and SRM banner.
    """
    buf = io.BytesIO() if output_path_or_buf is None else (
        output_path_or_buf if hasattr(output_path_or_buf, 'write') else open(output_path_or_buf, 'wb')
    )

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()

    # Times New Roman styles
    title_style = ParagraphStyle(
        'DL_Title',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=14,
        leading=17,
        alignment=1,
        textColor=colors.HexColor('#1C3022')
    )
    subtitle_style = ParagraphStyle(
        'DL_Sub',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=10.5,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#1E3A2F'),
        spaceBefore=2
    )
    meta_style = ParagraphStyle(
        'DL_Meta',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#556958'),
        spaceBefore=2
    )

    cell_style = ParagraphStyle(
        'DL_Cell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1F2937')
    )
    cell_bold = ParagraphStyle(
        'DL_CellBold',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#111827')
    )
    cell_center = ParagraphStyle(
        'DL_CellCenter',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8,
        leading=10.5,
        alignment=1,
        textColor=colors.HexColor('#1F2937')
    )
    cell_danger_center = ParagraphStyle(
        'DL_CellDangerCenter',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8,
        leading=10.5,
        alignment=1,
        textColor=colors.HexColor('#991B1B')
    )
    cell_success_center = ParagraphStyle(
        'DL_CellSuccessCenter',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8,
        leading=10.5,
        alignment=1,
        textColor=colors.HexColor('#166534')
    )
    cell_header = ParagraphStyle(
        'DL_CellHeader',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8,
        leading=10.5,
        alignment=1,  # Center aligned table titles
        textColor=colors.white
    )

    story = []

    # ── Header with SRM Banner ──
    lib_name = get_setting("library_name", "SRM EEE Department Library")
    today_str = datetime.now().strftime("%B %d, %Y • %I:%M %p")

    logo_file = _find_srm_logo()
    if logo_file and "banner" in logo_file:
        logo_flowable = Image(logo_file, width=145, height=61.9)
        logo_flowable.hAlign = 'CENTER'
        story.append(logo_flowable)
        story.append(Spacer(1, 3))
    elif logo_file:
        logo_flowable = Image(logo_file, width=48, height=48)
        logo_flowable.hAlign = 'CENTER'
        story.append(logo_flowable)
        story.append(Spacer(1, 3))

    story.append(Paragraph(f"Department of Electrical &amp; Electronics Engineering — {lib_name}", subtitle_style))

    # Build description of active filters
    dt_label = {"issue_date": "Issue Date", "due_date": "Due Date", "return_date": "Return Date"}.get(date_type, "Date")
    period_str = f"{from_date} to {to_date}" if (from_date and to_date) else (f"From {from_date}" if from_date else (f"Up to {to_date}" if to_date else "All Dates"))
    status_label = status.title() if status != 'all' else 'All Statuses'
    meta_line = f"Date-Wise Circulation Ledger &bull; Filtered by {dt_label}: <b>{period_str}</b> &bull; Status: <b>{status_label}</b> &bull; Generated on {today_str}"
    if query:
        meta_line += f" &bull; Search: \"{query}\""
    story.append(Paragraph(meta_line, meta_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1C3022'), spaceBefore=2, spaceAfter=8))

    # ── KPI Summary Cards Bar ──
    kpi_card_style = ParagraphStyle(
        'DL_KPI',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8,
        leading=11,
        alignment=1,
        textColor=colors.HexColor('#1F2937')
    )
    total_val = summary.get('total', len(transactions))
    issued_val = summary.get('issued', 0)
    ret_val = summary.get('returned', 0)
    overdue_val = summary.get('overdue', 0)
    fines_val = summary.get('total_fines', 0.0)

    kpi_data = [[
        Paragraph(f"<b>Total in Query</b><br/><font size='12'><b>{total_val}</b></font>", kpi_card_style),
        Paragraph(f"<b>Currently Borrowed</b><br/><font size='12' color='#0E7490'><b>{issued_val}</b></font>", kpi_card_style),
        Paragraph(f"<b>Returned</b><br/><font size='12' color='#166534'><b>{ret_val}</b></font>", kpi_card_style),
        Paragraph(f"<b>Overdue</b><br/><font size='12' color='#991B1B'><b>{overdue_val}</b></font>", kpi_card_style),
        Paragraph(f"<b>Accrued Fines</b><br/><font size='12' color='#B45309'><b>Rs. {fines_val:.2f}</b></font>", kpi_card_style),
    ]]
    kpi_tbl = Table(kpi_data, colWidths=[153, 153, 153, 153, 153])
    kpi_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAF6')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D1E0CE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2EBDD')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 10))

    # ── Circulation Records Table ──
    table_data = [[
        Paragraph("S.No", cell_header),
        Paragraph("Borrower Name", cell_header),
        Paragraph("Reg. / Staff No", cell_header),
        Paragraph("Role / Class", cell_header),
        Paragraph("Book Title", cell_header),
        Paragraph("Barcode / Acc", cell_header),
        Paragraph("Issue Date", cell_header),
        Paragraph("Due Date", cell_header),
        Paragraph("Return Date", cell_header),
        Paragraph("Status", cell_header),
        Paragraph("Fine", cell_header),
    ]]

    if transactions:
        for idx, t in enumerate(transactions, 1):
            st = t.get('status', '')
            if st == 'returned':
                st_p = Paragraph('Returned', cell_success_center)
            elif t.get('is_overdue'):
                st_p = Paragraph(f"Overdue ({t.get('overdue_days', 0)}d)", cell_danger_center)
            else:
                st_p = Paragraph('Borrowed', cell_center)
            
            role = (t.get('patron_type') or '').title()
            yr = t.get('patron_year')
            role_str = f"{role} ({yr})" if yr else role
            
            fine_val = t.get('fine_payable', 0.0)
            fine_p = Paragraph(f"Rs. {fine_val:.2f}" if fine_val > 0 else "—", cell_danger_center if fine_val > 0 else cell_center)

            acc_str = f" / {t.get('book_acc')}" if t.get('book_acc') else ""
            table_data.append([
                Paragraph(str(idx), cell_center),
                Paragraph(t.get('patron_name', ''), cell_bold),
                Paragraph(t.get('patron_reg', '') or "—", cell_center),
                Paragraph(role_str, cell_center),
                Paragraph(t.get('book_title', '')[:48], cell_style),
                Paragraph(f"{t.get('book_barcode', '')}{acc_str}", cell_center),
                Paragraph(t.get('issue_date', '') or "—", cell_center),
                Paragraph(t.get('due_date', '') or "—", cell_center),
                Paragraph(t.get('return_date', '') or "—", cell_center),
                st_p,
                fine_p
            ])

        # Printable width in Landscape A4 (margins 36pt): 841.89 - 72 = 769.89 pt. Total colWidths = 765 pt.
        t_ledger = Table(table_data, colWidths=[25, 120, 85, 65, 175, 75, 60, 60, 60, 50, 45], repeatRows=1)
        t_ledger.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1C3022')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_ledger)
    else:
        story.append(Paragraph("<i>No circulation records match the selected date range and filter criteria.</i>", cell_style))

    # ── Footer ──
    story.append(Spacer(1, 10))
    footer_text = "SRMIST Kattankulathur — Department of EEE Library Management System • Confidential Date-Wise Circulation Ledger"
    story.append(Paragraph(footer_text, meta_style))

    doc.build(story)

    if output_path_or_buf is None:
        buf.seek(0)
        return buf.read()
    elif not hasattr(output_path_or_buf, 'write'):
        buf.close()

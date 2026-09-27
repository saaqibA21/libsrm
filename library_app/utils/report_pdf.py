"""
Circulation & Analytics PDF Report Generator for SRM EEE Library
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

from library_app.database import (
    get_dashboard_stats, get_overdue_transactions,
    get_all_active_transactions, get_most_borrowed_books,
    get_most_active_patrons, get_setting
)


def generate_circulation_report_pdf(output_path_or_buf=None) -> bytes:
    """Generate a comprehensive editorial PDF report of library circulation and analytics."""
    buf = io.BytesIO() if output_path_or_buf is None else (
        output_path_or_buf if hasattr(output_path_or_buf, 'write') else open(output_path_or_buf, 'wb')
    )

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1C3022')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#4A5D4E')
    )
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#6B7D6E')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#16291C'),
        spaceBefore=12,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1F2937')
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#111827')
    )
    cell_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    cell_danger = ParagraphStyle(
        'TableDanger',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#991B1B')
    )

    story = []
    
    # ── Header ──
    lib_name = get_setting("library_name", "SRM EEE Department Library")
    today_str = datetime.now().strftime("%B %d, %Y • %I:%M %p")
    
    story.append(Paragraph("SRM Institute of Science & Technology", title_style))
    story.append(Paragraph(f"Department of Electrical & Electronics Engineering — {lib_name}", subtitle_style))
    story.append(Paragraph(f"Official Circulation & Analytics Report • Generated on {today_str}", meta_style))
    story.append(Spacer(1, 14))

    # ── Summary KPI Cards ──
    stats = get_dashboard_stats()
    fine_rate = float(get_setting("fine_per_day", "2.0"))
    
    kpi_data = [
        [
            Paragraph(f"<b>Total Catalog</b><br/><font size='14'><b>{stats['total_books']}</b></font>", cell_style),
            Paragraph(f"<b>On Shelf</b><br/><font size='14' color='#166534'><b>{stats['available_books']}</b></font>", cell_style),
            Paragraph(f"<b>Currently Borrowed</b><br/><font size='14' color='#0E7490'><b>{stats['issued_books']}</b></font>", cell_style),
            Paragraph(f"<b>Overdue Items</b><br/><font size='14' color='#991B1B'><b>{stats['overdue']}</b></font>", cell_style),
            Paragraph(f"<b>Registered Patrons</b><br/><font size='14' color='#7E22CE'><b>{stats['total_patrons']}</b></font>", cell_style),
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
    story.append(Paragraph(f"⚠️ Overdue Borrowed Books ({len(overdue)})", section_heading))
    
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
                Paragraph(txn.get("register_number","") or "—", cell_style),
                Paragraph(txn.get("book_title","")[:40], cell_style),
                Paragraph(txn.get("due_date",""), cell_danger),
                Paragraph(f"{days_over} days", cell_danger),
                Paragraph(f"₹{fine_val:.2f}", cell_danger),
            ])
        
        t_overdue = Table(overdue_table_data, colWidths=[105, 80, 177, 65, 55, 40])
        t_overdue.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991B1B')),
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
    story.append(Paragraph(f"📤 Active Book Circulation ({len(active)})", section_heading))
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
                st_color = cell_danger if days_left < 0 else cell_style
            except Exception:
                st_str = "Active"
                st_color = cell_style
            
            active_table_data.append([
                Paragraph(txn.get("patron_name",""), cell_bold),
                Paragraph(type_str, cell_style),
                Paragraph(txn.get("book_title","")[:45], cell_style),
                Paragraph(txn.get("issue_date",""), cell_style),
                Paragraph(txn.get("due_date",""), cell_style),
                Paragraph(st_str, st_color),
            ])
        
        t_active = Table(active_table_data, colWidths=[115, 75, 172, 60, 60, 40])
        t_active.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1C3022')),
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
    story.append(Paragraph("🏆 Most Borrowed Books (Circulation Frequency)", section_heading))
    if top_books:
        tb_data = [[
            Paragraph("Rank", cell_header),
            Paragraph("Book Title", cell_header),
            Paragraph("Author(s)", cell_header),
            Paragraph("Times Borrowed", cell_header),
        ]]
        for idx, b in enumerate(top_books, 1):
            tb_data.append([
                Paragraph(f"#{idx}", cell_bold),
                Paragraph(b.get("title",""), cell_bold),
                Paragraph(b.get("authors","") or "—", cell_style),
                Paragraph(f"<b>{b.get('borrow_count', 0)} times</b>", cell_style),
            ])
        t_tb = Table(tb_data, colWidths=[35, 237, 160, 90])
        t_tb.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#23432B')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (3,0), (3,-1), 'CENTER'),
        ]))
        story.append(t_tb)
    story.append(Spacer(1, 16))

    # ── Section 4: Most Active Borrowers ──
    top_patrons = get_most_active_patrons(10)
    story.append(Paragraph("🌟 Most Active Library Patrons", section_heading))
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
                Paragraph(f"#{idx}", cell_bold),
                Paragraph(p.get("name",""), cell_bold),
                Paragraph(p.get("register_number","") or "—", cell_style),
                Paragraph((p.get("patron_type","") or "").title(), cell_style),
                Paragraph(f"<b>{p.get('borrow_count', 0)} books</b>", cell_style),
            ])
        t_tp = Table(tp_data, colWidths=[35, 187, 110, 90, 100])
        t_tp.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A2F')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#F8FAF6'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1E0CE')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (4,0), (4,-1), 'CENTER'),
        ]))
        story.append(t_tp)

    # ── Footer / Signature ──
    story.append(Spacer(1, 25))
    footer_text = f"SRMIST Kattankulathur — Department of EEE Library Management System • Confidential Institutional Report"
    story.append(Paragraph(footer_text, meta_style))

    doc.build(story)
    
    if output_path_or_buf is None:
        buf.seek(0)
        return buf.read()
    elif not hasattr(output_path_or_buf, 'write'):
        buf.close()

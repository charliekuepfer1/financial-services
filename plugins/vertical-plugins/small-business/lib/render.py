#!/usr/bin/env python3
"""
render.py — render the books to a PDF the owner can open and file.

Usage:
    render.py <window>        window: today | wtd | mtd | season | YYYY-MM
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

LEDGER_PY = Path(__file__).with_name("ledger.py")
BOOKS_DIR = Path(os.environ.get("PD_BOOKS_DIR", Path.home() / ".premier-detailing-books"))


def call(*args: str) -> dict:
    out = subprocess.check_output([sys.executable, str(LEDGER_PY), *args])
    return json.loads(out.decode())


def fmt(n: float) -> str:
    return f"${n:,.2f}"


def render(window: str) -> Path:
    pl = call("pl", window)
    pj = call("per-job", f"--since={pl['start']}")
    al = call("anomalies")
    coa = json.loads((BOOKS_DIR / "chart-of-accounts.json").read_text())

    out_pdf = BOOKS_DIR / "pdf" / f"books-{window}-{date.today().isoformat()}.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    ink = colors.HexColor("#0E0E0E")
    muted = colors.HexColor("#5A5A5A")
    accent = colors.HexColor("#B45309")
    rule = colors.HexColor("#D4D4D4")
    danger = colors.HexColor("#B91C1C")
    ok = colors.HexColor("#15803D")

    doc = SimpleDocTemplate(
        str(out_pdf), pagesize=landscape(LETTER),
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.45 * inch, bottomMargin=0.45 * inch,
        title=f"Premier Detailing — Books {window}",
    )

    H = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=ink, spaceAfter=2)
    K = ParagraphStyle("K", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=accent, spaceAfter=4)
    S = ParagraphStyle("S", fontName="Helvetica", fontSize=9.5, leading=12, textColor=muted, spaceAfter=8)
    SH = ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=ink, spaceBefore=10, spaceAfter=4)
    A = ParagraphStyle("A", fontName="Helvetica", fontSize=9.5, leading=12, textColor=danger, spaceAfter=2)

    story = []
    story.append(Paragraph("PREMIER DETAILING", K))
    story.append(Paragraph(f"Books — {window} ({pl['start']} → {pl['end']})", H))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; "
        f"Stratford ON &nbsp;·&nbsp; HST: {coa['hst']['method']}",
        S,
    ))

    # Headline strip
    pace = pl["vs_target_pace"]
    headline_data = [
        ["Revenue (net)", "Expenses (net)", "Net income", "HST owed", "Window target", "Cash in (gross)"],
        [
            fmt(pl["revenue_total_net"]),
            fmt(pl["expense_total_net"]),
            fmt(pl["net_income"]),
            fmt(pl["hst_owed_to_cra"]),
            fmt(pace["window_target_cad"]),
            fmt(pl["cash_in_gross"]),
        ],
    ]
    headline = Table(headline_data, colWidths=[1.6 * inch] * 6)
    headline.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 1), (-1, 1), ink),
        ("LINEBELOW", (0, 0), (-1, 0), 0.3, rule),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, rule),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(headline)
    story.append(Spacer(1, 12))

    # Revenue by tier + Expenses by category, side-by-side
    rev_by_tier = pl["revenue_by_tier"]
    exp_by_cat = pl["expense_by_category"]

    rev_rows = [["Service tier", "Net revenue"]] + [
        [tier, fmt(v)] for tier, v in sorted(rev_by_tier.items(), key=lambda kv: -kv[1])
    ]
    exp_rows = [["Expense category", "Net spend"]] + [
        [coa["expenses"].get(c, {}).get("label", c), fmt(v)]
        for c, v in sorted(exp_by_cat.items(), key=lambda kv: -kv[1])
    ]

    def style_table(tbl: Table) -> Table:
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("TEXTCOLOR", (0, 0), (-1, 0), accent),
            ("FONTSIZE", (0, 1), (-1, -1), 9.5),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, rule),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    rev_tbl = style_table(Table(rev_rows, colWidths=[2.6 * inch, 1.4 * inch]))
    exp_tbl = style_table(Table(exp_rows, colWidths=[3.0 * inch, 1.4 * inch]))

    side = Table([[rev_tbl, exp_tbl]], colWidths=[4.2 * inch, 4.6 * inch])
    side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(Paragraph("REVENUE BY TIER &nbsp;&nbsp;·&nbsp;&nbsp; EXPENSES BY CATEGORY", K))
    story.append(side)

    # Per-job table
    story.append(Paragraph("PER-JOB PROFITABILITY (sorted lowest margin first)", K))
    if pj["jobs"]:
        rows = [["Job ID", "Customer", "Tier", "Revenue", "Chemicals", "Labor", "Travel", "Other", "Cost", "Margin", "Floor"]]
        for j in pj["jobs"]:
            rows.append([
                j["job_id"], j["customer"] or "", j["tier"] or "",
                fmt(j["revenue"]), fmt(j["chemicals"]), fmt(j["labor"]),
                fmt(j["travel"]), fmt(j["other"]), fmt(j["cost_total"]),
                f"{j['margin_pct']*100:.0f}%",
                f"{j['margin_floor']*100:.0f}%",
            ])
        pj_tbl = Table(rows, colWidths=[1.0, 1.4, 0.9, 0.9, 0.9, 0.8, 0.8, 0.7, 0.9, 0.7, 0.6])
        pj_tbl._argW = [c * inch for c in pj_tbl._argW]
        ts = TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, rule),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
            ("TEXTCOLOR", (0, 0), (-1, 0), accent),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ])
        for i, j in enumerate(pj["jobs"], start=1):
            if j["below_floor"]:
                ts.add("TEXTCOLOR", (-2, i), (-2, i), danger)
                ts.add("FONTNAME", (-2, i), (-2, i), "Helvetica-Bold")
        pj_tbl.setStyle(ts)
        story.append(pj_tbl)
    else:
        story.append(Paragraph("No jobs in window.", S))

    # Alerts
    story.append(Spacer(1, 10))
    story.append(Paragraph("ALERTS", K))
    if al["alerts"]:
        for a in al["alerts"]:
            story.append(Paragraph(f"• [{a['severity'].upper()}] {a['msg']}", A))
    else:
        story.append(Paragraph("No alerts. Books look clean.", ParagraphStyle("OK", parent=S, textColor=ok)))

    doc.build(story)
    print(json.dumps({"pdf": str(out_pdf)}, indent=2))
    return out_pdf


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: render.py <today|wtd|mtd|season|YYYY-MM>", file=sys.stderr)
        sys.exit(1)
    render(sys.argv[1])

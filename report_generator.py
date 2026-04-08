"""
PDF report generator.

Builds a multi-section PDF using ReportLab (layout/tables) and
Matplotlib (charts embedded as in-memory PNG images).
"""

import io
import calendar
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be set before other matplotlib imports
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable,
)

_REPORTS_DIR = Path(__file__).parent / "reports"

# Colour palette
_PALETTE = [
    "#4C9BE8", "#F2844B", "#57C98D", "#F5C842", "#A78BFA",
    "#F472B6", "#34D399", "#FB923C", "#60A5FA", "#A3E635",
    "#E879F9", "#94A3B8",
]

_styles = getSampleStyleSheet()
_h1 = ParagraphStyle("h1", parent=_styles["Heading1"], fontSize=20, spaceAfter=6)
_h2 = ParagraphStyle("h2", parent=_styles["Heading2"], fontSize=14, spaceAfter=4)
_body = _styles["BodyText"]
_small = ParagraphStyle("small", parent=_body, fontSize=8)

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
    ("FONTSIZE", (1, 1), (-1, -1), 8),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7F9FC"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
])


def _buf_to_rl_image(buf: io.BytesIO, width: float = 5.5 * inch) -> Image:
    """Convert a matplotlib PNG buffer to a ReportLab Image flowable."""
    buf.seek(0)
    img = Image(buf, width=width, height=width * 0.55)
    return img


def _pie_chart(by_category: dict[str, float]) -> io.BytesIO:
    labels = list(by_category.keys())
    values = [abs(v) for v in by_category.values()]
    palette = _PALETTE[: len(labels)]

    fig, ax = plt.subplots(figsize=(7, 4))
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%",
        colors=palette, startangle=140,
        pctdistance=0.82, wedgeprops={"linewidth": 0.5, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(7)
    ax.legend(
        wedges, [f"{l} (${v:,.2f})" for l, v in zip(labels, values)],
        loc="center left", bbox_to_anchor=(1, 0.5), fontsize=7,
    )
    ax.set_title("Spending by Category", fontsize=11, fontweight="bold")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf


def _bar_chart(history: list[dict]) -> io.BytesIO:
    recent = history[-6:]
    month_labels = [
        f"{calendar.month_abbr[r['month']]} {r['year']}" for r in recent
    ]
    totals = [r["total"] for r in recent]

    fig, ax = plt.subplots(figsize=(7, 3))
    bars = ax.bar(month_labels, totals, color=_PALETTE[0], edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, labels=[f"${v:,.0f}" for v in totals], fontsize=7, padding=3)
    ax.set_ylabel("Total Spend ($)", fontsize=8)
    ax.set_title("Monthly Spend — Last 6 Months", fontsize=11, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf


def generate_report(
    year: int,
    month: int,
    transactions_by_account: dict[str, list[dict]],
    history: list[dict],
) -> str:
    """
    Build the PDF report and return the file path.

    Args:
        year: Report year.
        month: Report month (1–12).
        transactions_by_account: Dict of account_name → list of enriched transaction dicts.
        history: All stored monthly summaries (from data_store.load_history).
    """
    _REPORTS_DIR.mkdir(exist_ok=True)
    output_path = _REPORTS_DIR / f"report_{year}_{month:02d}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    all_txns: list[dict] = []
    for txns in transactions_by_account.values():
        all_txns.extend(txns)

    # Aggregate spending by category (amounts in Plaid are positive = debit)
    by_category: dict[str, float] = defaultdict(float)
    for t in all_txns:
        amt = t.get("amount", 0)
        if amt > 0:  # exclude credits/transfers going in
            by_category[t.get("category_label", "Other")] += amt
    by_category = dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True))

    total_spend = sum(by_category.values())
    month_name = f"{calendar.month_name[month]} {year}"

    # ── Top merchants ──────────────────────────────────────────────────────────
    merchant_totals: dict[str, float] = defaultdict(float)
    for t in all_txns:
        if t.get("amount", 0) > 0:
            merchant_totals[t.get("name", "Unknown")] += t["amount"]
    top_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Account spend totals ───────────────────────────────────────────────────
    by_account: dict[str, float] = {}
    for acct, txns in transactions_by_account.items():
        by_account[acct] = sum(t.get("amount", 0) for t in txns if t.get("amount", 0) > 0)

    # ── Build flowables ────────────────────────────────────────────────────────
    story = []

    # Cover header
    story.append(Paragraph(f"Personal Finance Report", _h1))
    story.append(Paragraph(f"{month_name}", _h2))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1E3A5F")))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"<b>Total Spend:</b> ${total_spend:,.2f}", _body))
    story.append(Spacer(1, 0.3 * inch))

    # ── Section 1: Category breakdown ─────────────────────────────────────────
    story.append(Paragraph("1. Spending by Category", _h2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 0.1 * inch))

    if by_category:
        story.append(_buf_to_rl_image(_pie_chart(by_category)))
        story.append(Spacer(1, 0.15 * inch))

        cat_data = [["Category", "Amount", "% of Total"]]
        for cat, amt in by_category.items():
            pct = (amt / total_spend * 100) if total_spend else 0
            cat_data.append([cat, f"${amt:,.2f}", f"{pct:.1f}%"])
        cat_data.append(["TOTAL", f"${total_spend:,.2f}", "100%"])

        t = Table(cat_data, colWidths=[3.2 * inch, 1.5 * inch, 1.3 * inch])
        t.setStyle(_TABLE_STYLE)
        # Bold the totals row
        t.setStyle(TableStyle([
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8EEF7")),
        ]))
        story.append(t)

    story.append(PageBreak())

    # ── Section 2: Account-by-account ─────────────────────────────────────────
    story.append(Paragraph("2. Account-by-Account Breakdown", _h2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 0.1 * inch))

    for acct_name, txns in transactions_by_account.items():
        acct_spend = by_account.get(acct_name, 0)
        story.append(Paragraph(f"<b>{acct_name}</b> — Total: ${acct_spend:,.2f}", _body))
        story.append(Spacer(1, 0.06 * inch))

        if txns:
            df = pd.DataFrame(txns)[["date", "name", "category_label", "amount"]]
            df = df[df["amount"] > 0].sort_values("date", ascending=False)
            rows = [["Date", "Merchant / Description", "Category", "Amount"]]
            for _, row in df.iterrows():
                rows.append([
                    str(row["date"]),
                    str(row["name"])[:45],
                    str(row["category_label"]),
                    f"${row['amount']:,.2f}",
                ])
            tbl = Table(rows, colWidths=[0.9 * inch, 3.0 * inch, 1.6 * inch, 0.9 * inch])
            tbl.setStyle(_TABLE_STYLE)
            story.append(tbl)
        else:
            story.append(Paragraph("No transactions found for this account.", _small))

        story.append(Spacer(1, 0.25 * inch))

    story.append(PageBreak())

    # ── Section 3: Top merchants ───────────────────────────────────────────────
    story.append(Paragraph("3. Top 10 Merchants by Spend", _h2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 0.1 * inch))

    merchant_data = [["#", "Merchant", "Total Spend"]]
    for rank, (name, amt) in enumerate(top_merchants, 1):
        merchant_data.append([str(rank), name[:55], f"${amt:,.2f}"])

    mt = Table(merchant_data, colWidths=[0.4 * inch, 4.5 * inch, 1.1 * inch])
    mt.setStyle(_TABLE_STYLE)
    story.append(mt)
    story.append(PageBreak())

    # ── Section 4: Month-over-month trend ─────────────────────────────────────
    story.append(Paragraph("4. Month-over-Month Trend", _h2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 0.1 * inch))

    if len(history) >= 2:
        story.append(_buf_to_rl_image(_bar_chart(history), width=6.5 * inch))
        story.append(Spacer(1, 0.15 * inch))
        trend_data = [["Month", "Total Spend"]]
        for record in history[-6:]:
            label = f"{calendar.month_name[record['month']]} {record['year']}"
            trend_data.append([label, f"${record['total']:,.2f}"])
        tt = Table(trend_data, colWidths=[3 * inch, 2 * inch])
        tt.setStyle(_TABLE_STYLE)
        story.append(tt)
    else:
        story.append(Paragraph(
            "Not enough history for a trend chart yet. "
            "Run the report for at least 2 months to see this section.",
            _body,
        ))

    doc.build(story)
    return str(output_path)

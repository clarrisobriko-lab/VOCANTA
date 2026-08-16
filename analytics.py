from html import escape

from rich.console import Console
from rich.table import Table

from config.settings import APP_DISPLAY_NAME, EXPORT_DIR, SHORTLIST_SCORE
from core.database import Database
from core.follow_up_store import follow_up_statistics

ANALYTICS_FILE = EXPORT_DIR / "analytics.html"


def build_html(data, due_rows, follow_stats=None) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True); follow_stats=follow_stats or {}
    follow_up_cards = "".join(f"<article><h3>{escape(row['title'])}</h3><p><strong>{escape(row['company'])}</strong></p><p>Due: {escape(row['follow_up_date'] or '')}</p><a href=\"{escape(row['url'], quote=True)}\" target=\"_blank\">Open job</a></article>" for row in due_rows)
    health="".join(f'<div class="card"><div class="value">{follow_stats.get(key,0)}</div><div class="label">Follow-up {label}</div></div>' for key,label in [('pending','pending'),('completed','sent'),('failed','failed'),('cancelled','cancelled')])
    ANALYTICS_FILE.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{APP_DISPLAY_NAME} Analytics</title><style>body{{font-family:Arial,sans-serif;max-width:1050px;margin:30px auto;padding:0 18px;background:#f5f7fb;color:#111827}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}}.card,article{{background:white;border:1px solid #dbe1ea;border-radius:12px;padding:18px;box-shadow:0 3px 12px rgba(0,0,0,.05)}}.value{{font-size:30px;font-weight:700}} .label{{color:#4b5563}}section{{margin-top:30px}} a{{display:inline-block;margin-top:8px;color:#111827;font-weight:700}}</style></head><body><h1>{APP_DISPLAY_NAME} Pipeline Analytics</h1><div class="grid"><div class="card"><div class="value">{data['shortlisted']}</div><div class="label">Shortlisted</div></div><div class="card"><div class="value">{data['applied']}</div><div class="label">Applications</div></div><div class="card"><div class="value">{data['interviews']}</div><div class="label">Interviews</div></div><div class="card"><div class="value">{data['offers']}</div><div class="label">Offers</div></div>{health}</div><section><h2>Follow ups due</h2>{follow_up_cards or '<p>No follow ups are due.</p>'}</section></body></html>""",encoding="utf-8")


def main() -> int:
    console=Console(); database=Database()
    try:
        data=database.analytics(SHORTLIST_SCORE); due_rows=database.list_due_follow_ups(); stats=follow_up_statistics(database.connection)
        table=Table(title=f"{APP_DISPLAY_NAME} Pipeline Analytics"); table.add_column("Metric"); table.add_column("Value",justify="right")
        metrics=[("Shortlisted",data['shortlisted']),("Applications",data['applied']),("Interviews",data['interviews']),("Offers",data['offers']),("Follow-up pending",stats['pending']),("Follow-up sent",stats['completed']),("Follow-up failed",stats['failed']),("Follow-up cancelled",stats['cancelled'])]
        for label,value in metrics: table.add_row(label,str(value))
        console.print(table); build_html(data,due_rows,stats); return 0
    finally: database.close()


if __name__ == "__main__": raise SystemExit(main())

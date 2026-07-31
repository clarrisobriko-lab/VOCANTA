from html import escape

from rich.console import Console
from rich.table import Table

from config.settings import APP_DISPLAY_NAME, EXPORT_DIR, SHORTLIST_SCORE
from core.database import Database


ANALYTICS_FILE = EXPORT_DIR / "daily_summary.html"


def build_html(data, due_rows) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    follow_up_cards = "".join(
        f"""
        <article>
            <h3>{escape(row['title'])}</h3>
            <p><strong>{escape(row['company'])}</strong></p>
            <p>Due: {escape(row['follow_up_date'] or '')}</p>
            <a href="{escape(row['url'], quote=True)}" target="_blank">Open job</a>
        </article>
        """
        for row in due_rows
    )
    ANALYTICS_FILE.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VOCANTA Analytics</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1050px;margin:30px auto;padding:0 18px;background:#f5f7fb;color:#111827}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}}
.card,article{{background:white;border:1px solid #dbe1ea;border-radius:12px;padding:18px;box-shadow:0 3px 12px rgba(0,0,0,.05)}}
.value{{font-size:30px;font-weight:700}} .label{{color:#4b5563}}
section{{margin-top:30px}} a{{display:inline-block;margin-top:8px;color:#111827;font-weight:700}}
</style>
</head>
<body>
<h1>{APP_DISPLAY_NAME} Daily Summary</h1>
<div class="grid">
<div class="card"><div class="value">{data['shortlisted']}</div><div class="label">Shortlisted</div></div>
<div class="card"><div class="value">{data['applied']}</div><div class="label">Applications</div></div>
<div class="card"><div class="value">{data['follow_ups']}</div><div class="label">Follow ups</div></div>
<div class="card"><div class="value">{data['interviews']}</div><div class="label">Interviews</div></div>
<div class="card"><div class="value">{data['offers']}</div><div class="label">Offers</div></div>
<div class="card"><div class="value">{data['rejected']}</div><div class="label">Rejected</div></div>
<div class="card"><div class="value">{data['interview_rate']}%</div><div class="label">Interview rate</div></div>
<div class="card"><div class="value">{data['offer_rate']}%</div><div class="label">Offer rate</div></div>
</div>
<section>
<h2>Follow ups due</h2>
{follow_up_cards or '<p>No follow ups are due.</p>'}
</section>
</body>
</html>""",
        encoding="utf-8",
    )


def main() -> int:
    console = Console()
    database = Database()
    try:
        data = database.analytics(SHORTLIST_SCORE)
        due_rows = database.list_due_follow_ups()

        table = Table(title=f"{APP_DISPLAY_NAME} Daily Summary")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        for label, key in [
            ("Shortlisted", "shortlisted"),
            ("Applications", "applied"),
            ("Follow ups", "follow_ups"),
            ("Interviews", "interviews"),
            ("Offers", "offers"),
            ("Rejected", "rejected"),
            ("Interview rate", "interview_rate"),
            ("Offer rate", "offer_rate"),
        ]:
            value = data[key]
            suffix = "%" if "rate" in key else ""
            table.add_row(label, f"{value}{suffix}")
        console.print(table)

        if due_rows:
            due = Table(title="Follow Ups Due")
            due.add_column("ID")
            due.add_column("Company")
            due.add_column("Role")
            due.add_column("Due")
            for row in due_rows:
                due.add_row(
                    str(row["id"]),
                    row["company"],
                    row["title"],
                    row["follow_up_date"] or "",
                )
            console.print(due)

        build_html(data, due_rows)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

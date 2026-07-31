from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from core.database import Database

def main() -> int:
    c=Console(); d=Database()
    try:
        x=d.operational_briefing()
        c.print(Panel(f"Applications completed: {x['completed']}\nWaiting for review: {x['review']}\nBlocked by verification: {x['verification']}\nHuman action queue: {x['waiting']}\nHuman-completion emails: {x['emailed']}\nPotential sponsorship: {x['sponsor_jobs']}\nNGO opportunities: {x['ngo_jobs']}\nInterviews: {x['interviews']}\nOffers: {x['offers']}\nEstimated review time: {x['estimated_review_minutes']} minutes",title="VOCANTA Morning Brief",border_style="bright_blue"))
        if x['top_queue']:
            t=Table(expand=True); t.add_column('ID'); t.add_column('Opportunity'); t.add_column('Company'); t.add_column('Role',ratio=3); t.add_column('Status'); t.add_column('Visa')
            for r in x['top_queue']: t.add_row(str(r['job_id']),str(r['opportunity_score']),r['company'],r['title'],r['status'],r['sponsorship_label'])
            c.print(t)
        return 0
    finally: d.close()
if __name__=='__main__': raise SystemExit(main())

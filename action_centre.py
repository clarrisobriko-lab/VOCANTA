import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from config.settings import ACTION_CENTRE_MAX_ITEMS
from core.database import Database

def main() -> int:
    console=Console(); database=Database()
    try:
        while True:
            rows=database.list_human_action_queue(True,ACTION_CENTRE_MAX_ITEMS)
            console.clear(); console.print(Panel(f"{len(rows)} applications require human action.",title="VOCANTA Action Centre",border_style="bright_blue"))
            if not rows:
                console.print("[green]No unresolved applications.[/green]"); return 0
            table=Table(expand=True); table.add_column("ID"); table.add_column("Opportunity"); table.add_column("Company"); table.add_column("Role",ratio=3); table.add_column("Status"); table.add_column("Visa"); table.add_column("Email")
            for r in rows: table.add_row(str(r["job_id"]),str(r["opportunity_score"]),r["company"],r["title"],r["status"],r["sponsorship_label"],r["email_status"] or "NONE")
            console.print(table)
            answer=Prompt.ask("Job ID, or Enter to exit",default="",show_default=False).strip()
            if not answer: return 0
            if not answer.isdigit(): input("Numeric ID required. Press Enter: "); continue
            job_id=int(answer); row=next((r for r in rows if int(r["job_id"])==job_id),None)
            if row is None: input("Job not found. Press Enter: "); continue
            console.print(Panel(f"{row['company']}\n{row['title']}\n\nStatus: {row['status']}\nReason: {row['reason']}\nVisa: {row['sponsorship_label']}\nRelocation: {row['relocation_label']}\nEmail: {row['email_status']} {row['email_location']}\nURL: {row['url']}",title=f"Job {job_id}"))
            action=Prompt.ask("O open, D done, S skip, Enter back",default="",show_default=False).strip().upper()
            if action=='O': webbrowser.open(row['url'])
            elif action=='D': database.resolve_human_action(job_id,Prompt.ask("Resolution notes",default="Completed manually"))
            elif action=='S': database.resolve_human_action(job_id,Prompt.ask("Skip reason",default="Skipped after review"))
    finally: database.close()

if __name__=='__main__': raise SystemExit(main())

import logging
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.settings import AUTOMATION_MINIMUM_SCORE, MAX_CONNECTOR_WORKERS, MAX_DASHBOARD_ROWS, MINIMUM_SCORE, SHORTLIST_SCORE, STREAM_AUTOMATION_ON_DISCOVERY
from connectors.registry import get_connectors
from core.dashboard import Dashboard
from core.discovery import DiscoveryEngine
from core.database import Database
from core.exporter import export_jobs
from core.logging_config import configure_logging
from core.outcome_store import outcome_statistics
from core.revalidation import revalidate_existing_jobs
from intelligence.briefing import render_briefing


def fetch_connector(connector):
    try: return connector, list(connector.fetch_jobs()), None
    except Exception as exc: return connector, [], exc


def _phase(logger: logging.Logger, message: str, started: float | None = None) -> float:
    now = time.perf_counter()
    if started is None: logger.info(message)
    else: logger.info("%s completed in %.2f seconds", message, now - started)
    return now


def main() -> int:
    started = time.perf_counter(); configure_logging(); logger = logging.getLogger("vocanta")
    database = Database(); discovery = DiscoveryEngine(MINIMUM_SCORE); connectors = get_connectors()
    try:
        repaired_statuses = database.repair_job_statuses("STARTUP")
        for row in repaired_statuses: logger.info("Status repair | Job ID %s | %s -> NEW | %s | FOLLOW_UP had no confirmed submission evidence", row["id"], row["status"], row["company"])
        if repaired_statuses: logger.info("Repaired %s incorrect FOLLOW_UP job statuses", len(repaired_statuses))
        logger.info("Revalidated existing jobs: %s", revalidate_existing_jobs(database))
        accepted=[]; intelligence_by_url={}; seen_urls=set(); connector_stats={}; automation_process=None
        stream_marker=Path("data/.discovery_complete"); stream_marker.unlink(missing_ok=True)
        logger.info("Starting %s job connectors", len(connectors))
        with ThreadPoolExecutor(max_workers=min(MAX_CONNECTOR_WORKERS,max(1,len(connectors)))) as executor:
            futures={executor.submit(fetch_connector,c):c for c in connectors}
            for future in as_completed(futures):
                connector,jobs,error=future.result()
                if error is not None:
                    logger.warning("Connector failed, %s, %s",connector.name,error); connector_stats[connector.name]={"fetched":0,"accepted":0}; continue
                source_accepted=0; rejection_counts={}
                for job in jobs:
                    terminal_reason=database.terminal_automation_reason_for_url(job.url)
                    if terminal_reason:
                        rejection_counts["previously_terminal"]=rejection_counts.get("previously_terminal",0)+1; continue
                    result=discovery.evaluate(job,seen_urls)
                    if not result.accepted:
                        reason=str(result.rejection_reason or "unknown"); rejection_counts[reason]=rejection_counts.get(reason,0)+1; continue
                    scored_job=result.job; accepted.append(scored_job); intelligence_by_url[scored_job.url]=result.intelligence; source_accepted+=1
                source_jobs=accepted[-source_accepted:] if source_accepted else []
                if source_jobs:
                    database.upsert_jobs(source_jobs); database.upsert_job_intelligence_batch({j.url:intelligence_by_url[j.url] for j in source_jobs})
                    for queued_job in source_jobs:
                        stored=database.connection.execute("SELECT id FROM jobs WHERE url = ?",(queued_job.url,)).fetchone()
                        if stored is None: continue
                        decision=database.automation_queue_decision_for_job(stored["id"],AUTOMATION_MINIMUM_SCORE)
                        if decision is None: continue
                        accepted_for_queue=decision["reason"]=="ACCEPTED"
                        database.record_queue_audit(stored["id"],"DISCOVERY","ACCEPTED" if accepted_for_queue else "REJECTED",decision["reason"])
                    if STREAM_AUTOMATION_ON_DISCOVERY and automation_process is None and database.automation_queue_count(AUTOMATION_MINIMUM_SCORE)>0:
                        automation_process=subprocess.Popen([sys.executable,"stream_automation.py",str(stream_marker)],cwd=Path(__file__).resolve().parent)
                connector_stats[connector.name]={"fetched":len(jobs),"accepted":source_accepted,"rejected":len(jobs)-source_accepted}
                if rejection_counts: logger.info("%s rejection breakdown: %s",connector.name,rejection_counts)
        accepted.sort(key=lambda job:job.score,reverse=True); database.upsert_jobs(accepted); database.upsert_job_intelligence_batch(intelligence_by_url)
        try: database.refresh_employer_memory()
        except Exception: logger.exception("Employer memory refresh failed; startup will continue")
        rows=database.list_jobs(minimum_score=MINIMUM_SCORE,limit=MAX_DASHBOARD_ROWS); shortlisted=database.list_jobs(minimum_score=SHORTLIST_SCORE); export_jobs(shortlisted)
        dashboard=Dashboard(); render_briefing(dashboard.console,database.mission_briefing(SHORTLIST_SCORE))
        greenhouse_connector=next((c for c in connectors if c.name=="Greenhouse"),None); employer_stats=None
        if greenhouse_connector is not None and hasattr(greenhouse_connector,"registry"):
            employer_stats={**greenhouse_connector.registry.summary(),"boards":dict(getattr(greenhouse_connector,"last_board_stats",{}))}
        live_outcomes=outcome_statistics(database.connection)
        dashboard.show(rows,database.statistics(SHORTLIST_SCORE),connector_stats,employer_stats=employer_stats,outcome_stats=live_outcomes)
        stream_marker.parent.mkdir(parents=True,exist_ok=True); stream_marker.write_text("complete",encoding="utf-8")
        if database.automation_queue_count(AUTOMATION_MINIMUM_SCORE)>0:
            completed=subprocess.run([sys.executable,"runtime_queue.py"],cwd=Path(__file__).resolve().parent,check=False)
            if completed.returncode not in {0,2}: logger.error("Runtime application pipeline failed with exit code %s",completed.returncode)
        logger.info("VOCANTA completed in %.2f seconds",time.perf_counter()-started); return 0
    except KeyboardInterrupt:
        logger.warning("VOCANTA startup was cancelled by the user"); return 130
    finally:
        try:
            if 'stream_marker' in locals():
                stream_marker.parent.mkdir(parents=True,exist_ok=True); stream_marker.write_text("complete",encoding="utf-8")
        finally: database.close()


if __name__ == "__main__": raise SystemExit(main())

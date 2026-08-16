from __future__ import annotations

import os
from urllib.request import Request, urlopen

from automation.email_transport import SMTPFollowUpSender
from automation.follow_up_delivery import process_follow_ups
from automation.profile import load_profile
from core.database import Database
from intelligence.recipient_discovery import discover_verified_recipient


def fetch_public_job_text(url: str, *, timeout: int = 15) -> str:
    if not url.startswith(("http://", "https://")):
        return ""
    try:
        request=Request(url,headers={"User-Agent":"VOCANTA/1.0 follow-up recipient discovery"})
        with urlopen(request,timeout=timeout) as response:
            content_type=response.headers.get("Content-Type","")
            if "text" not in content_type and "html" not in content_type:
                return ""
            return response.read(1_000_000).decode("utf-8",errors="ignore")
    except Exception:
        return ""


def build_recipient_resolver(fetcher=fetch_public_job_text):
    def resolve(company: str, job_url: str) -> str:
        return discover_verified_recipient(fetcher(job_url),job_url)
    return resolve


def build_sender_from_environment() -> SMTPFollowUpSender:
    host=os.getenv("VOCANTA_SMTP_HOST","").strip()
    username=os.getenv("VOCANTA_SMTP_USERNAME","").strip()
    password=os.getenv("VOCANTA_SMTP_PASSWORD","")
    if not host or not username or not password:
        raise RuntimeError("Follow-up email is not configured. Set VOCANTA_SMTP_HOST, VOCANTA_SMTP_USERNAME and VOCANTA_SMTP_PASSWORD.")
    port=int(os.getenv("VOCANTA_SMTP_PORT","587"))
    from_address=os.getenv("VOCANTA_SMTP_FROM",username).strip()
    use_tls=os.getenv("VOCANTA_SMTP_TLS","1").strip().lower() not in {"0","false","no"}
    return SMTPFollowUpSender(host,port,username,password,from_address,use_tls=use_tls)


def run_follow_up_runtime(*, sender=None, recipient_resolver=None, now=None):
    profile=load_profile(); database=Database()
    try:
        sender=sender or build_sender_from_environment()
        recipient_resolver=recipient_resolver or build_recipient_resolver()
        return process_follow_ups(database.connection,profile.full_name,recipient_resolver,sender,now=now)
    finally:
        database.close()


def main() -> int:
    results=run_follow_up_runtime()
    sent=sum(1 for result in results if result.status=="SENT")
    pending=sum(1 for result in results if result.status in {"NO_RECIPIENT","FAILED"})
    print(f"VOCANTA follow-up runtime: {sent} sent, {pending} pending")
    return 0


if __name__=="__main__": raise SystemExit(main())

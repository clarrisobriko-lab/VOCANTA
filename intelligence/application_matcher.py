from __future__ import annotations

import re
from urllib.parse import urlparse


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+",(value or "").lower()) if len(token)>2}


def match_application(connection, sender: str, subject: str, body: str):
    sender_domain=(sender.rsplit("@",1)[1].lower() if "@" in sender else "")
    text_tokens=_tokens(f"{subject} {body}")
    rows=connection.execute("SELECT id,company,title,url,status FROM jobs WHERE applied=1 AND status IN ('APPLIED','FOLLOW_UP','INTERVIEW')").fetchall()
    ranked=[]
    for row in rows:
        company=str(row[1]); title=str(row[2]); url=str(row[3])
        company_tokens=_tokens(company); title_tokens=_tokens(title)
        host=(urlparse(url).hostname or "").lower().removeprefix("www.")
        score=0
        score += 4*len(company_tokens & text_tokens)
        score += 3*len(title_tokens & text_tokens)
        if sender_domain and host and (sender_domain==host or sender_domain.endswith("."+host) or host.endswith("."+sender_domain)): score += 6
        if score: ranked.append((score,int(row[0])))
    ranked.sort(reverse=True)
    if not ranked: return None
    if len(ranked)>1 and ranked[0][0]==ranked[1][0]: return None
    return ranked[0][1] if ranked[0][0]>=4 else None

from __future__ import annotations

import re
from urllib.parse import urlparse

EMAIL_RE=re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",re.I)
ROLE_PREFIXES=("jobs","careers","recruitment","recruiting","talent","hr","people")


def discover_verified_recipient(text: str, job_url: str) -> str:
    """Select only an explicitly published role mailbox; never synthesize an address."""
    candidates=list(dict.fromkeys(match.lower() for match in EMAIL_RE.findall(text or "")))
    if not candidates: return ""
    host=(urlparse(job_url).hostname or "").lower().removeprefix("www.")
    ranked=[]
    for email in candidates:
        local,domain=email.rsplit("@",1)
        role=any(local==prefix or local.startswith(prefix+".") or local.startswith(prefix+"-") for prefix in ROLE_PREFIXES)
        domain_match=bool(host and (domain==host or host.endswith("."+domain) or domain.endswith("."+host)))
        if role: ranked.append((2 if domain_match else 1,email))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else ""

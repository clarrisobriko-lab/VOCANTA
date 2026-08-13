import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "source",
    "sourceid",
    "gh_jid",
}

TRACKING_PREFIXES = (
    "utm_",
    "gh_src",
    "lever-",
)


def canonicalize_job_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not any(key.lower().startswith(prefix) for prefix in TRACKING_PREFIXES)
        and key.lower() not in TRACKING_PARAMETERS
    ]
    return urlunsplit((scheme, host, path, urlencode(sorted(query)), ""))


def stable_hash(value: object) -> str:
    if is_dataclass(value):
        value = asdict(value)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_hash(path: Path | str | None) -> str:
    if not path:
        return stable_hash("")
    resolved = Path(path)
    digest = hashlib.sha256()
    if not resolved.is_file():
        digest.update(f"missing:{resolved}".encode("utf-8"))
        return digest.hexdigest()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined_document_hash(paths: tuple[Path | str | None, ...]) -> str:
    return stable_hash([file_hash(path) for path in paths])


def application_idempotency_key(
    job_url: str,
    candidate_profile_hash: str,
    document_hash: str,
) -> str:
    return stable_hash(
        {
            "url": canonicalize_job_url(job_url),
            "candidate_profile_hash": candidate_profile_hash,
            "document_hash": document_hash,
        }
    )

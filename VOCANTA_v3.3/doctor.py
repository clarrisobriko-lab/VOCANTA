from __future__ import annotations

import argparse
import importlib
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from config.settings import (
    APP_DISPLAY_NAME,
    ASSETS_DIR,
    DATA_DIR,
    EXECUTIVE_ASSISTANT_CERTIFICATE_FILE,
    EXPORT_DIR,
    LOG_DIR,
    MASTER_COVER_LETTER_FILE,
    MASTER_CV_FILE,
    PACKAGE_ASSETS_DIR,
)


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    detail: str
    required: bool = True


def _dependency_check(module: str, required: bool = True) -> Check:
    try:
        importlib.import_module(module)
    except Exception as exc:
        return Check(f"dependency:{module}", False, str(exc), required)
    return Check(f"dependency:{module}", True, "available", required)


def _directory_check(path: Path) -> Check:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".vocanta_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return Check(f"directory:{path}", False, str(exc))
    return Check(f"directory:{path}", True, "writable")


def _asset_check(active: Path, packaged_name: str) -> Check:
    packaged = PACKAGE_ASSETS_DIR / packaged_name
    if active.is_file() or packaged.is_file():
        return Check(f"asset:{packaged_name}", True, "available")
    return Check(f"asset:{packaged_name}", False, "missing")


def _sqlite_check() -> Check:
    try:
        connection = sqlite3.connect(":memory:")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("CREATE TABLE healthcheck(id INTEGER PRIMARY KEY)")
        connection.close()
    except sqlite3.Error as exc:
        return Check("sqlite", False, str(exc))
    return Check("sqlite", True, sqlite3.sqlite_version)


def run_checks() -> list[Check]:
    checks = [
        Check("python", sys.version_info >= (3, 12), sys.version.split()[0]),
        _sqlite_check(),
        *(_directory_check(path) for path in (DATA_DIR, LOG_DIR, EXPORT_DIR, ASSETS_DIR)),
        _asset_check(MASTER_CV_FILE, "master_cv.docx"),
        _asset_check(MASTER_COVER_LETTER_FILE, "master_cover_letter.docx"),
        _asset_check(EXECUTIVE_ASSISTANT_CERTIFICATE_FILE, "executive_assistant_certificate.pdf"),
    ]
    for dependency in ("requests", "rich", "playwright", "keyring", "docx"):
        checks.append(_dependency_check(dependency))
    checks.append(_dependency_check("google.oauth2.credentials", required=False))
    checks.append(_dependency_check("google_auth_oauthlib.flow", required=False))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Verify {APP_DISPLAY_NAME} runtime readiness")
    parser.add_argument("--strict", action="store_true", help="also fail for optional integrations")
    args = parser.parse_args(argv)

    print(f"{APP_DISPLAY_NAME} production readiness check")
    failures = 0
    for check in run_checks():
        status = "PASS" if check.passed else "FAIL"
        requirement = "required" if check.required else "optional"
        print(f"[{status}] {check.name}: {check.detail} ({requirement})")
        if not check.passed and (check.required or args.strict):
            failures += 1
    if failures:
        print(f"Readiness check failed with {failures} blocking issue(s).")
        return 1
    print("Readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

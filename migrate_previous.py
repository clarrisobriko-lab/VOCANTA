import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

from config.settings import DATABASE_FILE, MIGRATION_MARKER_FILE
from core.backup import backup_database
from core.database import Database


VERSION_PATTERN = re.compile(r"VOCANTA_v(\d+(?:\.\d+)*)", re.IGNORECASE)


def version_from_path(path: Path) -> tuple[int, ...]:
    for part in reversed(path.parts):
        match = VERSION_PATTERN.search(part)
        if match:
            return tuple(int(piece) for piece in match.group(1).split("."))
    return (0,)


def discover_candidate_databases() -> list[Path]:
    roots = [Path.home() / "Downloads", Path.home() / "Desktop"]
    found: dict[str, Path] = {}
    current = DATABASE_FILE.resolve()
    for root in roots:
        if not root.exists():
            continue
        for candidate in root.rglob("vocanta.db"):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved == current:
                continue
            if "VOCANTA" not in str(candidate).upper():
                continue
            found[str(resolved).lower()] = candidate
    return list(found.values())


def inspect_database(path: Path) -> tuple[bool, int, str]:
    if not path.exists() or not path.is_file():
        return False, 0, "file missing"
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or str(integrity[0]).lower() != "ok":
                return False, 0, "integrity check failed"
            has_jobs = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'"
            ).fetchone()
            if has_jobs is None:
                return False, 0, "jobs table missing"
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
            required = {"id", "company", "title", "url"}
            missing = sorted(required - columns)
            if missing:
                return False, 0, f"jobs schema missing: {', '.join(missing)}"
            count = int(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
            return True, count, "valid SQLite database"
        finally:
            connection.close()
    except (sqlite3.Error, OSError) as exc:
        return False, 0, f"database error: {exc}"


def write_marker(source: Path | None, job_count: int) -> None:
    MIGRATION_MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    MIGRATION_MARKER_FILE.write_text(
        "\n".join([
            f"completed_at={datetime.now(timezone.utc).isoformat()}",
            f"source={source or 'fresh'}",
            f"job_count={job_count}",
        ]),
        encoding="utf-8",
    )


def migrate_database(source: Path) -> int:
    valid, source_jobs, reason = inspect_database(source)
    if not valid:
        print(f"Valid VOCANTA database not found: {reason}")
        return 1
    if DATABASE_FILE.exists():
        backup = backup_database(Path("backups"))
        if backup is not None:
            print(f"Current database backed up to: {backup}")
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    copy2(source, DATABASE_FILE)
    database = Database()
    try:
        repaired = database.repair_history()
        status_repairs = database.repair_job_statuses("MIGRATION")
    finally:
        database.close()
    write_marker(source, source_jobs)
    print(f"Migration completed from: {source}")
    print(f"Selection reason: highest valid numeric VOCANTA version; modified time used only as tie-breaker")
    print(f"History records repaired: {repaired}")
    print(f"Incorrect FOLLOW_UP statuses repaired: {len(status_repairs)}")
    for row in status_repairs:
        print(
            f"Status audit: Job ID {row['id']} | {row['status']} -> NEW | "
            "FOLLOW_UP had no confirmed submission evidence"
        )
    print(f"Active database: {DATABASE_FILE}")
    return 0


def automatic_mode() -> int:
    current_valid, current_jobs, _ = inspect_database(DATABASE_FILE)
    if MIGRATION_MARKER_FILE.exists() and current_valid:
        print(f"Active database ready: {DATABASE_FILE} ({current_jobs} jobs)")
        return 0
    if current_valid and current_jobs > 0:
        write_marker(None, current_jobs)
        print(f"Active database retained: {DATABASE_FILE} ({current_jobs} jobs)")
        return 0

    candidates = []
    rejected = []
    for candidate in discover_candidate_databases():
        valid, count, reason = inspect_database(candidate)
        version = version_from_path(candidate)
        try:
            modified = candidate.stat().st_mtime
        except OSError:
            modified = 0.0
        if valid and count > 0:
            candidates.append((version, modified, candidate, count))
        else:
            rejected.append((candidate, reason if not valid else "contains no jobs"))

    if not candidates:
        write_marker(None, 0)
        print("No previous valid VOCANTA database with jobs found. Starting fresh.")
        for path, reason in rejected[:10]:
            print(f"Skipped: {path} ({reason})")
        return 0

    version, _, source, count = max(candidates, key=lambda item: (item[0], item[1]))
    print(f"Automatically selected: {source} ({count} jobs)")
    print(f"Detected version: {'.'.join(map(str, version))}")
    print("Selection reason: highest valid numeric VOCANTA version; modified time used only as tie-breaker")
    return migrate_database(source)


def interactive_mode() -> int:
    candidates = discover_candidate_databases()
    print("VOCANTA manual database migration\n")
    for index, path in enumerate(candidates, start=1):
        valid, count, reason = inspect_database(path)
        version = ".".join(map(str, version_from_path(path)))
        status = f"VALID, {count} jobs, version {version}" if valid else f"INVALID, {reason}"
        print(f"{index}. {path} [{status}]")
    raw = input("\nChoose a number, paste a database path, or press Enter to cancel: ").strip()
    if not raw:
        return 0
    if raw.isdigit():
        selected = int(raw) - 1
        if selected < 0 or selected >= len(candidates):
            print("Invalid selection.")
            return 1
        source = candidates[selected]
    else:
        source = Path(raw.strip('"'))
    return migrate_database(source)


if __name__ == "__main__":
    raise SystemExit(interactive_mode() if "--manual" in sys.argv else automatic_mode())

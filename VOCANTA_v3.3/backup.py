from pathlib import Path
from core.backup import backup_database

def main() -> int:
    destination = backup_database(Path("backups"))
    print(f"Backup created: {destination}" if destination else "No database exists yet.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

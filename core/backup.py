from datetime import datetime
from pathlib import Path
from shutil import copy2
from config.settings import DATABASE_FILE

def backup_database(destination_dir: Path) -> Path | None:
    if not DATABASE_FILE.exists():
        return None
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"vocanta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    copy2(DATABASE_FILE, destination)
    return destination

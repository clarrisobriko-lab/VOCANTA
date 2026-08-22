from __future__ import annotations

import shutil
from pathlib import Path

from config.settings import EXECUTIVE_ASSISTANT_CERTIFICATE_FILE


def certificate_for_application(folder: Path) -> Path | None:
    """Copy the verified EA supporting certificate into an application package.

    Returns None when the configured source is unavailable. The helper never
    fabricates a certificate or substitutes another document.
    """
    source = Path(EXECUTIVE_ASSISTANT_CERTIFICATE_FILE)
    if not source.is_file():
        return None

    folder.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix or ".pdf"
    destination = folder / f"executive_assistant_certificate{suffix}"
    shutil.copy2(source, destination)
    return destination

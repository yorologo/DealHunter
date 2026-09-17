"""XDG-aware runtime paths shared by installed and checkout execution."""

import os
from pathlib import Path


def get_state_dir() -> Path:
    root = os.environ.get("XDG_STATE_HOME")
    if root:
        return Path(root).expanduser() / "dealhunter"
    return Path(os.path.expanduser("~/.local/state")) / "dealhunter"


def get_scheduler_log_path() -> Path:
    return get_state_dir() / "crawler-cron.log"

import os
import shutil
import subprocess

_wake_lock_active = False

def is_termux():
    """Check if running in Termux environment."""
    return os.environ.get("PREFIX", "") == "/data/data/com.termux/files/usr"

def has_wake_lock_cmd():
    """Check if termux-wake-lock command exists."""
    return shutil.which("termux-wake-lock") is not None

def acquire_wake_lock():
    """Attempt to acquire Termux wake lock."""
    global _wake_lock_active
    if not is_termux() or not has_wake_lock_cmd():
        return False
        
    try:
        subprocess.run(["termux-wake-lock"], check=True, capture_output=True)
        _wake_lock_active = True
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def is_wake_lock_active():
    """Check if wake lock was acquired successfully by this process."""
    return _wake_lock_active

import pytest
import os
import subprocess
from unittest.mock import patch
from dealhunter import termux
from dealhunter.doctor import _check_background_runtime

@pytest.fixture(autouse=True)
def reset_termux_state():
    termux._wake_lock_active = False
    yield
    termux._wake_lock_active = False

def test_desktop_unaffected():
    with patch.dict(os.environ, {"PREFIX": "/usr"}):
        assert not termux.is_termux()
        assert termux.acquire_wake_lock() is False
        assert termux.release_wake_lock() is False
        assert not termux.is_wake_lock_active()
        
        checks = _check_background_runtime()
        assert checks[0][1] == "N/A (Not Termux)"

def test_termux_detected():
    with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
        assert termux.is_termux()

def test_cmd_unavailable():
    with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
        with patch("shutil.which", return_value=None):
            assert not termux.has_wake_lock_cmd()
            assert termux.acquire_wake_lock() is False

def test_wake_lock_success():
    with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
        with patch("shutil.which", return_value="/bin/termux-wake-lock"):
            with patch("subprocess.run") as mock_run:
                assert termux.acquire_wake_lock() is True
                assert termux.is_wake_lock_active()
                mock_run.assert_called_with(["termux-wake-lock"], check=True, capture_output=True)
                
                # Check doctor
                checks = _check_background_runtime()
                names = {c[0]: c[1] for c in checks}
                assert names["Background Runtime (Termux)"] == "OK"
                assert names["Wake Lock"] == "ACTIVE"

def test_wake_lock_failure():
    with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
        with patch("shutil.which", return_value="/bin/termux-wake-lock"):
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
                assert termux.acquire_wake_lock() is False
                assert not termux.is_wake_lock_active()
                
                # Check doctor
                checks = _check_background_runtime()
                names = {c[0]: c[1] for c in checks}
                assert names["Background Runtime (Termux)"] == "WARNING"
                assert names["Wake Lock"] == "INACTIVE"
                assert "termux-wake-lock" in checks[0][2]

def test_release_wake_lock():
    with patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
        with patch("shutil.which", return_value="/bin/termux-wake-lock"):
            with patch("subprocess.run"):
                termux.acquire_wake_lock()
                assert termux.is_wake_lock_active()
                termux.release_wake_lock()
                assert not termux.is_wake_lock_active()

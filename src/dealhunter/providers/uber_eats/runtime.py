import asyncio
import logging
import os
import signal
import subprocess
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
USER_DATA_DIR_PATH = os.path.expanduser("~/.local/share/DealHunter/uber-chromium-profile")

class ChromiumRuntime:
    """Manages the lifecycle of a dedicated headless Chromium process."""
    
    def __init__(self, port=CDP_PORT, profile_path=USER_DATA_DIR_PATH):
        self.port = port
        self.profile_path = profile_path
        self._process = None

    def start(self):
        """Starts the local Chromium headless daemon."""
        if self.is_healthy():
            logger.info("Chromium runtime is already healthy and running.")
            return

        logger.info(f"Starting headless Chromium on port {self.port} with profile {self.profile_path}")
        os.makedirs(self.profile_path, exist_ok=True)
        
        # Remove SingletonLock in case of previous ungraceful shutdown
        lock_file = os.path.join(self.profile_path, "SingletonLock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except OSError:
                pass

        cmd = [
            "chromium-browser",
            "--headless",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.profile_path}",
            "about:blank"
        ]
        
        # Open in new process group to prevent it dying if parent shell exits
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        
        # Wait for it to become healthy
        for i in range(10):
            if self.is_healthy():
                logger.info("Chromium runtime started and is healthy.")
                return
            time.sleep(1)
            
        self.stop()
        raise RuntimeError("Chromium failed to start or did not become healthy within 10 seconds.")

    def stop(self):
        """Stops the Chromium process safely."""
        if self._process:
            logger.info("Stopping Chromium runtime...")
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error while stopping Chromium: {e}")
                
            self._process = None
        else:
            # Fallback: if we didn't start it but we want to ensure it's dead
            try:
                subprocess.run(["pkill", "-f", "chromium-browser.*uber-chromium-profile"], check=False)
            except Exception:
                pass

    def is_running_local(self) -> bool:
        """Detect this dedicated Chromium process without HTTP/CDP traffic."""
        if self._process is not None and self._process.poll() is None:
            return True

        profile_arg = f"--user-data-dir={self.profile_path}"
        try:
            for entry in os.scandir("/proc"):
                if not entry.name.isdigit():
                    continue
                try:
                    with open(os.path.join(entry.path, "cmdline"), "rb") as handle:
                        raw = handle.read()
                    args = [part.decode("utf-8", "ignore") for part in raw.split(b"\0") if part]
                except (OSError, PermissionError):
                    continue
                if not args:
                    continue
                executable = os.path.basename(args[0])
                if executable in ("chromium-browser", "chromium") and profile_arg in args:
                    return True
        except OSError:
            pass
        return False

    def is_healthy(self) -> bool:
        """Returns True if the CDP endpoint is reachable."""
        url = f"http://{CDP_HOST}:{self.port}/json/version"
        try:
            req = urllib.request.urlopen(url, timeout=2)
            if req.status == 200:
                return True
        except Exception:
            return False
        return False

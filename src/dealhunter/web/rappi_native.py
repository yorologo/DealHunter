"""Open an exact Rappi store through the verified native Android deep link."""

import shlex
import shutil
import subprocess
import threading
from urllib.parse import urlencode


RAPPI_PACKAGE = "com.grability.rappi"
RAPPI_DEEP_LINK_BASE = "gbrappi://com.grability.rappi"
NAVIGATION_LOCK = threading.Lock()

_NATIVE_STORE_TYPES = {
    "restaurant": "restaurant",
    "restaurants": "restaurant",
    "market": "market",
    "chiper_home": "chiper_home",
    "chiper_extended": "chiper_extended",
}


class RappiNavigationError(RuntimeError):
    """Base error for native Rappi navigation."""


class RappiNavigationBusy(RappiNavigationError):
    """Another client is already controlling Rappi."""


class UnsupportedStoreType(RappiNavigationError):
    """The installed Rappi app contract was not verified for this store type."""


def build_store_deep_link(store_id, store_type):
    """Build a fixed-package native URI from server-owned store metadata."""
    native_type = _NATIVE_STORE_TYPES.get((store_type or "").casefold())
    if native_type is None:
        raise UnsupportedStoreType(store_type or "<empty>")
    if not store_id or not str(store_id).isdigit():
        raise ValueError("store_id must be numeric")

    query = urlencode({"store_type": native_type, "store_id": str(store_id)})
    return f"{RAPPI_DEEP_LINK_BASE}?{query}"


def open_store_in_rappi(store_id, store_type):
    """Deliver the exact-store deep link as Android shell through Shizuku."""
    uri = build_store_deep_link(store_id, store_type)
    rish = shutil.which("rish")
    if not rish:
        raise RappiNavigationError("rish/Shizuku no está disponible")

    if not NAVIGATION_LOCK.acquire(blocking=False):
        raise RappiNavigationBusy("Rappi ya está procesando otra navegación")

    try:
        command = " ".join(
            (
                "/system/bin/am start -W --user 0",
                "-a android.intent.action.VIEW",
                f"-d {shlex.quote(uri)}",
                f"-p {RAPPI_PACKAGE}",
            )
        )
        try:
            result = subprocess.run(
                [rish, "-c", command],
                capture_output=True,
                text=True,
                timeout=8,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RappiNavigationError("No fue posible ejecutar el Intent nativo") from exc

        output = "\n".join((result.stdout or "", result.stderr or "")).casefold()
        failed = (
            result.returncode != 0
            or "status: ok" not in output
            or "unable to resolve intent" in output
            or "error: activity not started" in output
            or "securityexception" in output
        )
        if failed:
            raise RappiNavigationError("Rappi rechazó el Intent de tienda")
        return uri
    finally:
        NAVIGATION_LOCK.release()

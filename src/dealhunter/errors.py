"""Structured error handling for DealHunter."""

import json
import sqlite3
import socket
import urllib.error


ERROR_CATALOG = {
    "NETWORK_ERROR": {
        "message": "Network connection failed",
        "recoverable": True,
        "recommended_action": "Check network connection and retry",
    },
    "TIMEOUT": {
        "message": "Request timed out",
        "recoverable": True,
        "recommended_action": "Retry after a moment",
    },
    "HTTP_429": {
        "message": "Rate limited by server (HTTP 429)",
        "recoverable": True,
        "recommended_action": "Wait before retrying. Do not increase request rate",
    },
    "CLOUDFLARE_LIMIT": {
        "message": "Blocked by Cloudflare (HTTP 1015)",
        "recoverable": False,
        "recommended_action": "Stop requests. Wait at least 5 minutes",
    },
    "INVALID_RESPONSE": {
        "message": "Server returned invalid or unparseable response",
        "recoverable": True,
        "recommended_action": "Retry the request",
    },
    "PARSER_ERROR": {
        "message": "Failed to parse response data",
        "recoverable": False,
        "recommended_action": "Report this issue",
    },
    "DB_LOCKED": {
        "message": "Database is locked by another process",
        "recoverable": True,
        "recommended_action": "Close other processes using the database",
    },
    "DB_CORRUPT": {
        "message": "Database file is corrupted",
        "recoverable": False,
        "recommended_action": "Restore from backup using: rappi-ofertas db backup",
    },
    "CONFIG_ERROR": {
        "message": "Configuration error",
        "recoverable": True,
        "recommended_action": "Check config with: rappi-ofertas config show",
    },
    "PARTIAL_RUN": {
        "message": "Run completed partially with some data collected",
        "recoverable": True,
        "recommended_action": "Re-run to collect remaining data",
    },
    "REQUEST_BUDGET_REACHED": {
        "message": "Maximum request budget reached",
        "recoverable": False,
        "recommended_action": "Increase --max-requests or accept partial results",
    },
}


class DealHunterError(Exception):
    """Structured error with code, recoverability and recommended action."""

    def __init__(self, code, message=None, recoverable=None, recommended_action=None):
        defaults = ERROR_CATALOG.get(code, {})
        self.code = code
        self.message = message or defaults.get("message", "Unknown error")
        self.recoverable = recoverable if recoverable is not None else defaults.get("recoverable", False)
        self.recommended_action = recommended_action or defaults.get("recommended_action", "")
        super().__init__(self.message)

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "recommended_action": self.recommended_action,
        }

    def __str__(self):
        recover = "recoverable" if self.recoverable else "non-recoverable"
        return f"[{self.code}] {self.message} ({recover})"


def classify_error(exc):
    """Classify a Python exception into a structured DealHunterError."""
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return DealHunterError("HTTP_429")
        if exc.code == 1015:
            return DealHunterError("CLOUDFLARE_LIMIT")
        return DealHunterError("NETWORK_ERROR", message=f"HTTP {exc.code}: {exc.reason}")

    if isinstance(exc, urllib.error.URLError):
        return DealHunterError("NETWORK_ERROR", message=str(exc.reason))

    if isinstance(exc, (socket.timeout, TimeoutError)):
        return DealHunterError("TIMEOUT")

    if isinstance(exc, json.JSONDecodeError):
        return DealHunterError("INVALID_RESPONSE", message="Invalid JSON in response")

    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        if "locked" in msg:
            return DealHunterError("DB_LOCKED")
        return DealHunterError("DB_CORRUPT", message=str(exc))

    if isinstance(exc, sqlite3.DatabaseError):
        msg = str(exc).lower()
        if "corrupt" in msg or "malformed" in msg:
            return DealHunterError("DB_CORRUPT")
        return DealHunterError("DB_LOCKED", message=str(exc))

    return DealHunterError("NETWORK_ERROR", message=str(exc))

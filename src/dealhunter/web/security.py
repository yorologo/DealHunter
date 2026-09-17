"""Small Web security helpers shared by redirecting routes."""

from urllib.parse import urlsplit


def local_redirect_target(candidate, *, host, default=None):
    """Return a local/same-origin redirect target, or ``default`` when unsafe."""
    if not candidate:
        return default
    candidate = str(candidate).strip()
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme in ("http", "https") and parsed.netloc == host:
            return candidate
        return default
    if not candidate.startswith("/") or candidate.startswith("//"):
        return default
    return candidate

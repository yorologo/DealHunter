"""Small, shared HTTP query-parameter validators for DealHunter Web."""

import base64
import json
import math


class QueryParamError(ValueError):
    """Raised when a client query parameter is malformed or out of contract."""


def parse_int(value, *, name, default=None, minimum=None, maximum=None):
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise QueryParamError(f"{name} must be an integer") from exc
    if minimum is not None and parsed < minimum:
        raise QueryParamError(f"{name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise QueryParamError(f"{name} must be <= {maximum}")
    return parsed


def parse_float(value, *, name, default=None, minimum=None, maximum=None):
    if value in (None, ""):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise QueryParamError(f"{name} must be a number") from exc
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        raise QueryParamError(f"{name} must be finite")
    if minimum is not None and parsed < minimum:
        raise QueryParamError(f"{name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise QueryParamError(f"{name} must be <= {maximum}")
    return parsed


def parse_enum(value, *, name, allowed, default=None):
    if value in (None, ""):
        return default
    if value not in allowed:
        raise QueryParamError(f"{name} has an unsupported value")
    return value


def parse_page(value):
    return parse_int(value, name="page", default=1, minimum=1, maximum=100000)


def parse_limit(value, *, default=25, maximum=100):
    return parse_int(value, name="limit", default=default, minimum=1, maximum=maximum)


def encode_cursor(values):
    """Encode opaque keyset values for URLs without exposing implementation syntax."""
    payload = {"v": 1, "k": list(values)}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def parse_cursor(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str) or len(value) > 2048:
        raise QueryParamError("cursor is malformed")
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise QueryParamError("cursor is malformed") from exc
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise QueryParamError("cursor has an unsupported version")
    keys = payload.get("k")
    if not isinstance(keys, list) or len(keys) != 7:
        raise QueryParamError("cursor has an invalid shape")
    for item in keys:
        if isinstance(item, bool) or not isinstance(item, (str, int, float)):
            raise QueryParamError("cursor has an invalid value")
        if isinstance(item, float) and not math.isfinite(item):
            raise QueryParamError("cursor has a non-finite value")
        if isinstance(item, str) and len(item) > 512:
            raise QueryParamError("cursor value is too long")
    if not all(isinstance(item, str) for item in keys[-3:]):
        raise QueryParamError("cursor identity is invalid")
    return keys

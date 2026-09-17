import json
import math
import os
import tempfile
import tomllib

from .errors import DealHunterError
from .providers.registry import KNOWN_PROVIDERS, validate_provider

KNOWN_MEMBERSHIPS = ("rappi_pro", "uber_one")
MEMBERSHIP_STATUSES = ("active", "inactive", "unknown")
COMPARISON_POLICIES = ("exclude", "show_but_exclude", "include")
DISCOVERY_MODES = ("normal", "deep", "full")
SORT_OPTIONS = ("discount", "price", "store", "name", "deal-score", "historical-discount")
TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off"}


def parse_strict_bool(value):
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError("boolean must be one of true/false, 1/0, yes/no, on/off")


def validate_membership(name):
    if name not in KNOWN_MEMBERSHIPS:
        raise ValueError(f"unsupported membership: {name}")
    return name


def validate_membership_status(status):
    if status not in MEMBERSHIP_STATUSES:
        raise ValueError(f"unsupported membership status: {status}")
    return status


def validate_comparison_policy(policy):
    if policy not in COMPARISON_POLICIES:
        raise ValueError(f"unsupported comparison policy: {policy}")
    return policy


def parse_location(lat, lng):
    """Validate one complete location pair and return normalized floats."""
    if lat is None or lng is None or str(lat).strip() == "" or str(lng).strip() == "":
        raise ValueError("both lat and lng are required")
    try:
        lat_value = float(lat)
        lng_value = float(lng)
    except (TypeError, ValueError) as exc:
        raise ValueError("lat/lng must be numeric") from exc
    if not -90 <= lat_value <= 90:
        raise ValueError("lat must be between -90 and 90")
    if not -180 <= lng_value <= 180:
        raise ValueError("lng must be between -180 and 180")
    return lat_value, lng_value



def get_config_dir():
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return os.path.join(xdg_config, "dealhunter")
    return os.path.expanduser("~/.config/dealhunter")


def get_config_path():
    return os.path.join(get_config_dir(), "config.toml")


def load_config():
    path = get_config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise DealHunterError("CONFIG_ERROR", message=f"Could not read {path}: {exc}") from exc


def save_config(config_dict):
    path = get_config_path()
    directory = os.path.dirname(path)
    temp_path = None
    try:
        content = _dump_toml(config_dict) + "\n"
        os.makedirs(directory, mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            prefix=".config.toml.",
            suffix=".tmp",
            delete=False,
        ) as f:
            temp_path = f.name
            os.chmod(temp_path, 0o600)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
        temp_path = None
        os.chmod(path, 0o600)
        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except (OSError, TypeError, ValueError) as exc:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
        raise DealHunterError("CONFIG_ERROR", message=f"Could not save {path}: {exc}") from exc


def _dump_toml(d, prefix=""):
    if not isinstance(d, dict):
        raise TypeError("TOML root must be a table")
    lines = []

    for k, v in d.items():
        if not isinstance(v, dict):
            lines.append(f"{_dump_key(k)} = {_dump_value(v)}")

    for k, v in d.items():
        if isinstance(v, dict):
            if lines:
                lines.append("")
            key = _dump_key(k)
            section = f"{prefix}.{key}" if prefix else key
            lines.append(f"[{section}]")
            nested = _dump_toml(v, section)
            if nested:
                lines.append(nested)

    return "\n".join(lines).strip()


def _dump_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise ValueError("non-finite floats are not supported")
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        if any(isinstance(item, (dict, list)) for item in v):
            raise TypeError("nested arrays and inline tables are not supported")
        types = {type(item) for item in v}
        if len(types) > 1:
            raise TypeError("TOML arrays must contain one value type")
        return "[" + ", ".join(_dump_value(item) for item in v) + "]"
    raise TypeError(f"unsupported TOML value: {type(v).__name__}")


def _dump_key(value):
    if not isinstance(value, str) or not value:
        raise TypeError("TOML keys must be non-empty strings")
    return json.dumps(value, ensure_ascii=False)


def _deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v
    return d


def get_default_config():
    """Return a fresh copy of the canonical DealHunter defaults."""
    return {
        "lat": None,
        "lng": None,
        "min_discount": 0,
        "max_discount": 100,
        "min_price": None,
        "max_price": None,
        "promo": [],
        "only_nxm": False,
        "min_promo_discount": None,
        "status": [],
        "discovery_mode": "full",
        "radius": 5.0,
        "top": 50,
        "sort": "discount",
        "desc": True,
        "output_format": "table",
        "vertical": [],
        "store": [],
        "exclude_store": [],
        "query": [],
        "exclude": [],
        "max_requests": 1000,
        "max_runtime": 3600,
        "compact": False,
        "dry_run": False,
        "providers": {
            "rappi": {"enabled": True},
            "uber_eats": {"enabled": True},
        },
        "memberships": {
            "rappi_pro": {"status": "unknown"},
            "uber_one": {"status": "unknown"},
        },
        "comparison": {
            "inactive_membership_offers": "show_but_exclude",
        },
    }


def get_merged_config(cli_args, profile_name=None):
    config = get_default_config()

    global_cfg = load_config()
    for k in config.keys():
        if k in global_cfg:
            if isinstance(config[k], dict) and isinstance(global_cfg[k], dict):
                _deep_update(config[k], global_cfg[k])
            else:
                config[k] = global_cfg[k]

    if profile_name and "profiles" in global_cfg and profile_name in global_cfg["profiles"]:
        profile_cfg = global_cfg["profiles"][profile_name]
        for k in config.keys():
            if k in profile_cfg:
                if isinstance(config[k], dict) and isinstance(profile_cfg[k], dict):
                    _deep_update(config[k], profile_cfg[k])
                else:
                    config[k] = profile_cfg[k]

    if cli_args:
        for k, v in vars(cli_args).items():
            if v is not None and k in config:
                if isinstance(v, list) and len(v) == 0:
                    continue
                config[k] = v

    return config

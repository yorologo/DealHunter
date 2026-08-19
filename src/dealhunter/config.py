import os
import tomllib

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
    with open(path, "rb") as f:
        try:
            return tomllib.load(f)
        except Exception:
            return {}

def save_config(config_dict):
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(_dump_toml(config_dict))

def _dump_toml(d, prefix=""):
    lines = []
    # Dump simple types first
    for k, v in d.items():
        if not isinstance(v, dict):
            lines.append(f"{k} = {_dump_value(v)}")
            
    # Dump nested dicts
    for k, v in d.items():
        if isinstance(v, dict):
            if lines:
                lines.append("")
            section = f"{prefix}.{k}" if prefix else k
            lines.append(f"[{section}]")
            lines.append(_dump_toml(v, section))
            
    return "\n".join(lines).strip()

def _dump_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    elif isinstance(v, (int, float)):
        return str(v)
    elif isinstance(v, str):
        return f'"{v}"'
    elif isinstance(v, list):
        items = ", ".join(_dump_value(i) for i in v)
        return f"[{items}]"
    return '""'

def get_merged_config(cli_args, profile_name=None):
    # defaults
    config = {
        "min_discount": 0,
        "max_discount": 100,
        "radius": 5.0,
        "top": 50,
        "sort": "discount",
        "output_format": "table",
        "vertical": [],
        "store": [],
        "exclude_store": [],
        "query": [],
        "exclude": [],
        "max_requests": 1000,
        "max_runtime": 3600,
        "compact": False,
        "dry_run": False
    }
    
    # global config
    global_cfg = load_config()
    for k in config.keys():
        if k in global_cfg:
            config[k] = global_cfg[k]
            
    # profile
    if profile_name and "profiles" in global_cfg and profile_name in global_cfg["profiles"]:
        profile_cfg = global_cfg["profiles"][profile_name]
        for k in config.keys():
            if k in profile_cfg:
                config[k] = profile_cfg[k]
                
    # cli override
    if cli_args:
        for k, v in vars(cli_args).items():
            if v is not None and k in config:
                if isinstance(v, list) and len(v) == 0:
                    continue # empty lists from CLI shouldn't override config lists
                if isinstance(v, bool) and not v:
                    continue # False flags might be default, let's be careful. Actually, argparse defaults might overwrite.
                config[k] = v
                
    return config


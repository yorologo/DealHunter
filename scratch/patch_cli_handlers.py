import re

with open("src/dealhunter/cli.py", "r") as f:
    content = f.read()

handlers_code = """
    from dealhunter.config import load_config, save_config

    if args.command == "providers":
        cfg = load_config()
        provs = cfg.get("providers", {})
        print("Providers:")
        for p in ["rappi", "uber_eats"]:
            status = provs.get(p, {}).get("enabled", True)
            print(f"  {p}: {'Enabled' if status else 'Disabled'}")
        return

    if args.command == "provider":
        cfg = load_config()
        if "providers" not in cfg:
            cfg["providers"] = {}
        if args.name not in cfg["providers"]:
            cfg["providers"][args.name] = {}
        cfg["providers"][args.name]["enabled"] = (args.action == "enable")
        save_config(cfg)
        print(f"Provider {args.name} has been {args.action}d.")
        return

    if args.command == "memberships":
        cfg = load_config()
        mems = cfg.get("memberships", {})
        print("Memberships:")
        for m in ["rappi_pro", "uber_one"]:
            status = mems.get(m, {}).get("status", "unknown")
            print(f"  {m}: {status}")
        return

    if args.command == "membership":
        cfg = load_config()
        if "memberships" not in cfg:
            cfg["memberships"] = {}
        if args.name not in cfg["memberships"]:
            cfg["memberships"][args.name] = {}
        cfg["memberships"][args.name]["status"] = args.action
        save_config(cfg)
        print(f"Membership {args.name} is now {args.action}.")
        return

    if args.command == "comparison":
        cfg = load_config()
        if "comparison" not in cfg:
            cfg["comparison"] = {}
        if args.policy == "membership-policy":
            cfg["comparison"]["inactive_membership_offers"] = args.value
        save_config(cfg)
        print(f"Comparison policy updated.")
        return

    if args.command == "db":
"""

content = content.replace('    if args.command == "db":', handlers_code)

with open("src/dealhunter/cli.py", "w") as f:
    f.write(content)


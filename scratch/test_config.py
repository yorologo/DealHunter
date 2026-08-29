from dealhunter.config import _dump_toml
d = {
    "providers": {
        "rappi": {"enabled": True},
        "uber_eats": {"enabled": False}
    },
    "comparison": {
        "inactive_membership_offers": "show_but_exclude"
    }
}
print(_dump_toml(d))

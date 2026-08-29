import tomllib
toml_str = """
[providers]
[providers.rappi]
enabled = true

[providers.uber_eats]
enabled = false

[comparison]
inactive_membership_offers = "show_but_exclude"
"""
print(tomllib.loads(toml_str))

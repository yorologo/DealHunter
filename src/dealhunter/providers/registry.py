# dealhunter/providers/registry.py

# Extensible registry of known providers.
# This defines the domains DealHunter knows about, independently of which are enabled.
KNOWN_PROVIDERS = {
    "rappi",
    "uber_eats"
}

def is_known_provider(provider: str) -> bool:
    """Check if a provider is known to DealHunter."""
    if not provider:
        return False
    return provider.lower() in KNOWN_PROVIDERS

def validate_provider(provider: str):
    """
    Validates a provider for new writes.
    Raises ValueError if the provider is not known.
    """
    if not is_known_provider(provider):
        raise ValueError(f"Unknown provider: '{provider}'. Must be one of {KNOWN_PROVIDERS}")

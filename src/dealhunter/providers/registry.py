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

def normalize_provider(provider: str) -> str:
    """
    Normalizes a provider string to its canonical internal representation.
    Raises ValueError if the provider is not known.
    """
    if not provider:
        raise ValueError(f"Provider cannot be empty. Must be one of {KNOWN_PROVIDERS}")
    p_lower = provider.lower()
    if p_lower not in KNOWN_PROVIDERS:
        raise ValueError(f"Unknown provider: '{provider}'. Must be one of {KNOWN_PROVIDERS}")
    return p_lower

def validate_provider(provider: str) -> str:
    """
    Validates a provider for new writes and returns the canonicalized string.
    Raises ValueError if the provider is not known.
    """
    return normalize_provider(provider)

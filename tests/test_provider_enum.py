import pytest
from dealhunter.providers.registry import validate_provider

def test_provider_enum_validation():
    validate_provider("rappi")
    validate_provider("uber_eats")
    
    with pytest.raises(ValueError):
        validate_provider("Uber1")
        
    with pytest.raises(ValueError):
        validate_provider("invalid")

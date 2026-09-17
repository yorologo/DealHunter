from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_security_policy_matches_session_capabilities():
    text = (ROOT / "SECURITY.md").read_text()
    assert "NO maneja autenticaciones" not in text
    assert "SecretStore" in text
    assert "opt-in" in text
    assert "RAPPI_BEARER_TOKEN" in text
    assert "plaintext" in text


def test_account_diagnostics_does_not_claim_sessions_are_never_persisted():
    text = (ROOT / "docs" / "account-diagnostics.md").read_text()
    assert "never persisted by DealHunter" not in text
    assert "SecretStore" in text
    assert "persistentes" in text
    assert "SQLite" in text

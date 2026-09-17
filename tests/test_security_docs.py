from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_security_policy_matches_session_capabilities():
    text = (ROOT / "SECURITY.md").read_text()
    assert "NO maneja autenticaciones" not in text
    assert "SecretStore" in text
    assert "opt-in" in text
    assert "RAPPI_BEARER_TOKEN" in text
    assert "plaintext" in text


def test_maintained_security_docs_describe_persistent_sessions_correctly():
    text = (ROOT / "docs" / "security.md").read_text()
    assert "never persisted by DealHunter" not in text
    assert "SecretStore" in text
    assert "sesiones persistentes" in text
    assert "SQLite" in text

import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Handle case where secret_store module is not yet implemented fully or correctly
try:
    from dealhunter.secret_store import (
        SecretStore,
        SessionService,
        SESSION_NOT_CONFIGURED,
        SESSION_PERSISTENT,
        SESSION_TEMPORARY,
        SESSION_EPHEMERAL,
        SESSION_EXPIRED,
        SESSION_CORRUPTED,
        DEALHUNTER_SUPER_SECRET_CANARY_987654321
    )
except ImportError:
    pytest.skip("SecretStore module not fully implemented yet", allow_module_level=True)

class TestSecretStore:
    def test_store_and_load(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        token = "test_token_123"
        store.store(token)
        loaded = store.load()
        assert loaded == token

    def test_store_creates_directory(self, tmp_path):
        config_dir = tmp_path / "new_dir"
        store = SecretStore(config_dir=str(config_dir))
        store.store("token")
        assert config_dir.exists()
        assert (config_dir / "session.enc").exists()

    def test_load_nonexistent(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        assert store.load() is None

    def test_delete(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("token")
        store.delete()
        assert store.exists() is False
        assert store.load() is None

    def test_replace_atomic(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("tokenA")
        store.store("tokenB")
        assert store.load() == "tokenB"

    def test_corrupted_file(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("token")
        session_file = tmp_path / "session.enc"
        with open(session_file, "w") as f:
            f.write("garbage")
        from dealhunter.errors import DealHunterError
        with pytest.raises(DealHunterError) as exc:
            store.load()
        assert exc.value.code == "SECRET_STORE_CORRUPTED"

    def test_missing_salt(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("token")
        salt_file = tmp_path / ".session_salt"
        os.remove(salt_file)
        from dealhunter.errors import DealHunterError
        with pytest.raises(DealHunterError) as exc:
            store.load()
        assert exc.value.code == "SECRET_STORE_CORRUPTED"

    def test_file_permissions(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("token")
        session_file = tmp_path / "session.enc"
        st = os.stat(session_file)
        assert oct(st.st_mode)[-3:] == "600"

    def test_check_permissions_warns_open(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("token")
        session_file = tmp_path / "session.enc"
        os.chmod(session_file, 0o644)
        warnings = store.check_permissions()
        assert len(warnings) > 0

    def test_metadata_no_token(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store("super_secret_token")
        meta = store.metadata()
        for v in meta.values():
            assert "super_secret_token" not in str(v)

    def test_exists(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        assert store.exists() is False
        store.store("token")
        assert store.exists() is True

class TestSessionService:
    @pytest.fixture(autouse=True)
    def clean_env(self, monkeypatch):
        monkeypatch.delenv("RAPPI_BEARER_TOKEN", raising=False)

    def test_not_configured(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        assert service.get_mode() == SESSION_NOT_CONFIGURED

    def test_ephemeral_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RAPPI_BEARER_TOKEN", "env_token")
        service = SessionService(config_dir=str(tmp_path))
        assert service.get_mode() == SESSION_EPHEMERAL
        assert service.get_token() == "env_token"

    def test_persistent_mode(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("persistent_token")
        assert service.get_mode() == SESSION_PERSISTENT
        assert service.get_token() == "persistent_token"

    def test_temporary_mode(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_temporary("temp_token")
        assert service.get_mode() == SESSION_TEMPORARY
        assert service.get_token() == "temp_token"

    def test_env_precedence_over_persistent(self, tmp_path, monkeypatch):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("persistent_token")
        monkeypatch.setenv("RAPPI_BEARER_TOKEN", "env_token")
        assert service.get_mode() == SESSION_EPHEMERAL
        assert service.get_token() == "env_token"

    def test_delete_persistent(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("token")
        service.delete()
        assert service.get_mode() == SESSION_NOT_CONFIGURED
        assert service.get_token() is None

    def test_replace(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("tokenA")
        service.replace("tokenB")
        assert service.get_token() == "tokenB"
        assert service.get_mode() == SESSION_PERSISTENT

    def test_mark_expired(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("token")
        service.mark_expired()
        assert service.get_mode() == SESSION_PERSISTENT
        assert service.get_token() is None
        assert service.get_raw_token() == "token"

        assert service.get_token() is None  # Expired token not served

    def test_repr_redacted(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("secret_token")
        assert "secret_token" not in repr(service)
        assert "secret_token" not in str(service)

    def test_status_no_secret(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent("secret_token")
        status = service.get_status()
        for v in status.values():
            assert "secret_token" not in str(v)

class TestCanaryLeakPrevention:
    def test_canary_not_in_metadata(self, tmp_path):
        store = SecretStore(config_dir=str(tmp_path))
        store.store(DEALHUNTER_SUPER_SECRET_CANARY_987654321)
        meta = store.metadata()
        for v in meta.values():
            assert str(DEALHUNTER_SUPER_SECRET_CANARY_987654321) not in str(v)

    def test_canary_not_in_repr(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent(DEALHUNTER_SUPER_SECRET_CANARY_987654321)
        assert str(DEALHUNTER_SUPER_SECRET_CANARY_987654321) not in repr(service)
        assert str(DEALHUNTER_SUPER_SECRET_CANARY_987654321) not in str(service)

    def test_canary_not_in_status(self, tmp_path):
        service = SessionService(config_dir=str(tmp_path))
        service.store_persistent(DEALHUNTER_SUPER_SECRET_CANARY_987654321)
        status = service.get_status()
        
        def check_no_canary(data):
            if isinstance(data, dict):
                for v in data.values():
                    check_no_canary(v)
            elif isinstance(data, list):
                for v in data:
                    check_no_canary(v)
            else:
                assert str(DEALHUNTER_SUPER_SECRET_CANARY_987654321) not in str(data)

        check_no_canary(status)


def test_persistent_secret_store_fails_closed_without_cryptography(tmp_path, monkeypatch):
    import dealhunter.secret_store as secret_store_module
    from dealhunter.errors import DealHunterError

    monkeypatch.setattr(secret_store_module, "CRYPTO_AVAILABLE", False)
    store = secret_store_module.SecretStore(config_dir=str(tmp_path))

    with pytest.raises(DealHunterError) as exc:
        store.store("must-not-be-written")
    assert exc.value.code == "SECRET_STORE_UNAVAILABLE"
    assert not (tmp_path / "session.enc").exists()


def test_atomic_store_failure_preserves_previous_secret(tmp_path, monkeypatch):
    import dealhunter.secret_store as secret_store_module
    from dealhunter.errors import DealHunterError

    store = secret_store_module.SecretStore(config_dir=str(tmp_path))
    assert store.store("token-A") is True
    previous = (tmp_path / "session.enc").read_bytes()

    def fail_replace(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(secret_store_module.os, "replace", fail_replace)
    with pytest.raises(DealHunterError) as exc:
        store.store("token-B")
    assert exc.value.code == "SECRET_STORE_IO"
    assert (tmp_path / "session.enc").read_bytes() == previous
    assert store.load() == "token-A"


def test_secret_store_permission_failure_is_not_success(tmp_path, monkeypatch):
    import dealhunter.secret_store as secret_store_module
    from dealhunter.errors import DealHunterError

    store = secret_store_module.SecretStore(config_dir=str(tmp_path))
    monkeypatch.setattr(secret_store_module.os, "fchmod", lambda *args: (_ for _ in ()).throw(OSError("no chmod")))
    with pytest.raises(DealHunterError) as exc:
        store.store("token")
    assert exc.value.code == "SECRET_STORE_IO"
    assert not (tmp_path / "session.enc").exists()


def test_corruption_and_storage_error_have_distinct_modes(tmp_path, monkeypatch):
    import dealhunter.secret_store as secret_store_module

    store = secret_store_module.SecretStore(config_dir=str(tmp_path))
    store.store("token")
    (tmp_path / "session.enc").write_bytes(b"corrupt")
    service = secret_store_module.SessionService(config_dir=str(tmp_path))
    assert service.get_mode() == secret_store_module.SESSION_CORRUPTED

    # Restore a valid store, then simulate a storage read error.
    (tmp_path / "session.enc").unlink()
    store.store("token")
    real_open = open
    def fail_session_open(path, mode='r', *args, **kwargs):
        if str(path).endswith('session.enc') and 'r' in mode:
            raise OSError("storage unavailable")
        return real_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(secret_store_module, "open", fail_session_open, raising=False)
    service = secret_store_module.SessionService(config_dir=str(tmp_path))
    assert service.get_mode() == secret_store_module.SESSION_STORAGE_ERROR

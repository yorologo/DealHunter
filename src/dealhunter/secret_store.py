"""
Core secure credential storage abstraction for DealHunter.
Handles encrypted storage and retrieval of session tokens.
"""

import os
import stat
import json
import base64
import platform
from datetime import datetime, timezone
import getpass
import logging
import time
import tempfile
from typing import Optional, Dict, Any, List

from .errors import DealHunterError

logger = logging.getLogger(__name__)

# Secure persistent storage requires authenticated encryption.
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
    ENCRYPTION_METHOD = 'Fernet (AES-128)'
except ImportError:
    CRYPTO_AVAILABLE = False
    ENCRYPTION_METHOD = 'unavailable'

# Session Modes
SESSION_NOT_CONFIGURED = 'NOT_CONFIGURED'
SESSION_PERSISTENT = 'PERSISTENT'
SESSION_TEMPORARY = 'TEMPORARY'
SESSION_EPHEMERAL = 'EPHEMERAL'  # from env var
SESSION_EXPIRED = 'EXPIRED'
SESSION_CORRUPTED = 'CORRUPTED'
SESSION_STORAGE_ERROR = 'STORAGE_ERROR'

# Test helper
DEALHUNTER_SUPER_SECRET_CANARY_987654321 = "secret_canary_value"


class SecretStore:
    """
    Handles secure on-disk storage of secrets.
    Uses PBKDF2-HMAC to derive an encryption key from device entropy and a random salt.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            home = os.path.expanduser('~')
            self.config_dir = os.path.join(home, '.config', 'dealhunter')
        else:
            self.config_dir = config_dir
            
        self.session_file = os.path.join(self.config_dir, 'session.enc')
        self.salt_file = os.path.join(self.config_dir, '.session_salt')
        self._ensure_dir()

    def __repr__(self) -> str:
        return f'<SecretStore config_dir={self.config_dir}>'

    def _ensure_dir(self):
        """Ensure config directory exists privately or fail closed."""
        try:
            os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
            os.chmod(self.config_dir, 0o700)
            mode = os.stat(self.config_dir).st_mode
        except OSError as exc:
            raise DealHunterError("SECRET_STORE_IO", message=f"Cannot secure config directory: {exc}") from exc
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise DealHunterError("SECRET_STORE_IO", message="Config directory permissions are not private")

    def _enforce_file_perms(self, path: str):
        """Enforce and verify 0600 permissions or fail closed."""
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            mode = os.stat(path).st_mode
        except OSError as exc:
            raise DealHunterError("SECRET_STORE_IO", message=f"Cannot secure secret file: {exc}") from exc
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise DealHunterError("SECRET_STORE_IO", message="Secret file permissions are not private")

    def _atomic_write_private(self, path: str, payload: bytes):
        """Write temp -> fsync -> private permissions -> atomic replace."""
        self._ensure_dir()
        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", dir=self.config_dir)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                fd = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            mode = os.stat(tmp_path).st_mode
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise OSError("temporary secret permissions are not private")
            os.replace(tmp_path, path)
            tmp_path = None
        except OSError as exc:
            raise DealHunterError("SECRET_STORE_IO", message=f"Atomic secret write failed: {exc}") from exc
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp_path is not None:
                try:
                    os.remove(tmp_path)
                except FileNotFoundError:
                    pass

    def check_permissions(self) -> List[str]:
        """Check if files have appropriate permissions. Return warnings."""
        warnings = []
        
        if os.path.exists(self.config_dir):
            st = os.stat(self.config_dir)
            if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                warnings.append(f"Directory {self.config_dir} has overly permissive access (should be 0700).")
                
        for f in [self.session_file, self.salt_file]:
            if os.path.exists(f):
                st = os.stat(f)
                if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                    warnings.append(f"File {f} has overly permissive access (should be 0600).")
                    
        return warnings

    def _get_device_entropy(self) -> bytes:
        """Gather device-specific entropy."""
        components = []
        
        # User
        try:
            components.append(getpass.getuser())
        except Exception:
            components.append('unknown_user')
            
        # Node/hostname
        components.append(platform.node() or 'unknown_node')
        
        # Machine ID (Linux specific)
        machine_id_paths = ['/etc/machine-id', '/var/lib/dbus/machine-id']
        machine_id = ''
        for p in machine_id_paths:
            try:
                if os.path.exists(p):
                    with open(p, 'r') as f:
                        machine_id = f.read().strip()
                    break
            except Exception:
                pass
        components.append(machine_id)
        
        # Pepper
        components.append('dealhunter-v1-pepper')
        
        entropy = "|".join(components)
        return entropy.encode('utf-8')

    @staticmethod
    def _require_crypto():
        if not CRYPTO_AVAILABLE:
            raise DealHunterError("SECRET_STORE_UNAVAILABLE")

    def _get_or_create_salt(self) -> bytes:
        """Get the existing 16-byte salt or create it atomically."""
        if os.path.exists(self.salt_file):
            try:
                with open(self.salt_file, 'rb') as handle:
                    salt = handle.read()
            except OSError as exc:
                raise DealHunterError("SECRET_STORE_IO", message=f"Cannot read session salt: {exc}") from exc
            if len(salt) != 16:
                raise DealHunterError("SECRET_STORE_CORRUPTED", message="Session salt is invalid")
            self._enforce_file_perms(self.salt_file)
            return salt

        salt = os.urandom(16)
        self._atomic_write_private(self.salt_file, salt)
        return salt

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from device entropy + salt."""
        self._require_crypto()
        entropy = self._get_device_entropy()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(entropy))

    def store(self, token: str, is_expired: bool = False, last_validation_status: str = None, last_validated_at: str = None) -> bool:
        """Encrypt and atomically persist token; failures are explicit."""
        self._require_crypto()
        self._ensure_dir()
        salt = self._get_or_create_salt()
        key = self._derive_key(salt)
        data = {
            'stored_at': time.time(),
            'token': token,
            'is_expired': is_expired,
            'last_validation_status': last_validation_status,
            'last_validated_at': last_validated_at,
            'encryption': ENCRYPTION_METHOD,
        }
        encrypted = Fernet(key).encrypt(json.dumps(data).encode('utf-8'))
        self._atomic_write_private(self.session_file, encrypted)
        return True

    def load_with_metadata(self) -> dict:
        """Load metadata, distinguishing absence, corruption and storage errors."""
        if not os.path.exists(self.session_file):
            return None
        self._require_crypto()
        if not os.path.exists(self.salt_file):
            raise DealHunterError("SECRET_STORE_CORRUPTED", message="Encrypted session exists without its salt")
        try:
            with open(self.session_file, 'rb') as handle:
                encrypted = handle.read()
            with open(self.salt_file, 'rb') as handle:
                salt = handle.read()
        except OSError as exc:
            raise DealHunterError("SECRET_STORE_IO", message=f"Cannot read secure session storage: {exc}") from exc
        if len(salt) != 16 or not encrypted:
            raise DealHunterError("SECRET_STORE_CORRUPTED", message="Secure session storage is incomplete")
        try:
            key = self._derive_key(salt)
            raw_data = Fernet(key).decrypt(encrypted)
            return json.loads(raw_data.decode('utf-8'))
        except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise DealHunterError("SECRET_STORE_CORRUPTED", message="Secure session cannot be decrypted") from exc

    def load(self) -> Optional[str]:
        """Load and decrypt token."""
        data = self.load_with_metadata()
        if data:
            return data.get('token')
        return None

    def delete(self) -> bool:
        """Securely delete session and salt files."""
        success = True
        for f in [self.session_file, self.salt_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as e:
                    logger.error(f"Failed to delete {f}: {e}")
                    success = False
        return success

    def exists(self) -> bool:
        """Check if encrypted session file exists."""
        return os.path.exists(self.session_file)

    def metadata(self) -> Dict[str, Any]:
        """Return safe metadata without collapsing corruption/storage failures."""
        meta = {
            'storage_secure': True,
            'encryption_method': ENCRYPTION_METHOD,
            'mode': SESSION_NOT_CONFIGURED,
            'stored_at': None,
        }
        if not self.exists():
            return meta
        self._require_crypto()
        try:
            data = self.load_with_metadata()
            meta['mode'] = SESSION_PERSISTENT
            meta['stored_at'] = data.get('stored_at') if data else None
        except DealHunterError as exc:
            if exc.code == "SECRET_STORE_CORRUPTED":
                meta['mode'] = SESSION_CORRUPTED
            elif exc.code == "SECRET_STORE_IO":
                meta['mode'] = SESSION_STORAGE_ERROR
            else:
                raise
        return meta

class SessionService:
    """
    High-level abstraction for session management.
    """
    def __init__(self, config_dir: Optional[str] = None):
        self.store = SecretStore(config_dir=config_dir)
        self._temp_token = None
        self._temp_is_expired = False
        
    @property
    def _is_expired(self):
        if getattr(self, '_temp_is_expired', False):
            return True
        data = self.store.load_with_metadata()
        if data and data.get('is_expired'):
            return True
        return False
        
    @_is_expired.setter
    def _is_expired(self, value):
        self._temp_is_expired = value

    def __repr__(self) -> str:
        return '<SessionService (redacted)>'

    def get_token(self) -> Optional[str]:
        """Get the current session token (Ephemeral > Temporary > Persistent)."""
        if self._is_expired:
            return None
            
        ephemeral = os.environ.get('RAPPI_BEARER_TOKEN')
        if ephemeral:
            return ephemeral
            
        if self._temp_token:
            return self._temp_token
            
        return self.store.load()

    def get_mode(self) -> str:
        """Return source mode while preserving corruption vs storage failures."""
        if os.environ.get('RAPPI_BEARER_TOKEN'):
            return SESSION_EPHEMERAL
        if self._temp_token:
            return SESSION_TEMPORARY
        if self.store.exists():
            try:
                if self.store.load_with_metadata() is None:
                    return SESSION_CORRUPTED
                return SESSION_PERSISTENT
            except DealHunterError as exc:
                if exc.code == "SECRET_STORE_CORRUPTED":
                    return SESSION_CORRUPTED
                if exc.code == "SECRET_STORE_IO":
                    return SESSION_STORAGE_ERROR
                raise
        return SESSION_NOT_CONFIGURED

    def get_token(self) -> Optional[str]:
        """Get the current session token (Ephemeral > Temporary > Persistent)."""
        if self._is_expired:
            return None
            
        ephemeral = os.environ.get('RAPPI_BEARER_TOKEN')
        if ephemeral:
            return ephemeral
            
        if self._temp_token:
            return self._temp_token
            
        return self.store.load()
        
    def get_raw_token(self) -> Optional[str]:
        """Get the token even if marked as expired."""
        ephemeral = os.environ.get('RAPPI_BEARER_TOKEN')
        if ephemeral:
            return ephemeral
            
        if self._temp_token:
            return self._temp_token
            
        return self.store.load()

    def get_status(self) -> Dict[str, Any]:
        """Returns safe session status metadata."""
        mode = self.get_mode()
        warnings = self.store.check_permissions()
        
        status = {
            'mode': mode,
            'configured': mode in (SESSION_PERSISTENT, SESSION_TEMPORARY, SESSION_EPHEMERAL),
            'valid': mode in (SESSION_PERSISTENT, SESSION_TEMPORARY, SESSION_EPHEMERAL),
            'stored_at': None,
            'encryption_method': ENCRYPTION_METHOD,
            'warnings': warnings
        }
        
        if mode == SESSION_PERSISTENT:
            meta = self.store.metadata()
            status['stored_at'] = meta.get('stored_at')
            
        return status

    def store_persistent(self, token: str) -> bool:
        """Store via SecretStore."""
        self._is_expired = False
        self._temp_token = None
        return self.store.store(token)

    def store_temporary(self, token: str):
        """Store in memory only."""
        self._is_expired = False
        self._temp_token = token

    def delete(self) -> bool:
        """Delete persistent session and clear temporary/expired state."""
        self._temp_token = None
        self._is_expired = False
        return self.store.delete()

    def replace(self, new_token: str) -> bool:
        """Atomic replace (store new)."""
        return self.store_persistent(new_token)

    def mark_expired(self):
        """Mark session as expired without deleting."""
        self._temp_is_expired = True
        data = self.store.load_with_metadata()
        if data and data.get('token'):
            self.store.store(data['token'], is_expired=True, last_validation_status="EXPIRED", last_validated_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if 'datetime' in globals() else None)

    def update_validation(self, status: str, timestamp: str):
        """Update the last validation status and timestamp."""
        data = self.store.load_with_metadata()
        if data and data.get('token'):
            # Preserve existing is_expired unless status changes it explicitly
            is_expired = data.get('is_expired', False)
            if status == "EXPIRED":
                is_expired = True
                self._temp_is_expired = True
            elif status == "VALID":
                is_expired = False
                self._temp_is_expired = False
            self.store.store(
                data['token'],
                is_expired=is_expired,
                last_validation_status=status,
                last_validated_at=timestamp
            )

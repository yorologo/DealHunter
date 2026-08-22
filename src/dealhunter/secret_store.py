"""
Core secure credential storage abstraction for DealHunter.
Handles encrypted storage and retrieval of session tokens.
"""

import os
import stat
import json
import base64
import hashlib
import platform
import getpass
import logging
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Try to import cryptography, fallback to itsdangerous
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
    ENCRYPTION_METHOD = 'Fernet (AES-128)'
except ImportError:
    try:
        from itsdangerous import URLSafeSerializer
        CRYPTO_AVAILABLE = False
        ENCRYPTION_METHOD = 'itsdangerous.URLSafeSerializer (HMAC Sign-only Fallback)'
    except ImportError:
        CRYPTO_AVAILABLE = False
        ENCRYPTION_METHOD = 'Plaintext (UNSAFE FALLBACK)'
        logger.error("Neither cryptography nor itsdangerous available. Storing secrets insecurely!")

# Session Modes
SESSION_NOT_CONFIGURED = 'NOT_CONFIGURED'
SESSION_PERSISTENT = 'PERSISTENT'
SESSION_TEMPORARY = 'TEMPORARY'
SESSION_EPHEMERAL = 'EPHEMERAL'  # from env var
SESSION_EXPIRED = 'EXPIRED'
SESSION_CORRUPTED = 'CORRUPTED'

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
        """Ensure config directory exists with correct permissions (0700)."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
        else:
            # Enforce permissions if it exists
            try:
                os.chmod(self.config_dir, 0o700)
            except Exception as e:
                logger.warning(f"Could not set permissions on config dir: {e}")

    def _enforce_file_perms(self, path: str):
        """Enforce 0600 permissions on a file."""
        if os.path.exists(path):
            try:
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                logger.warning(f"Could not set permissions on file {path}: {e}")

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

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new one and store it securely."""
        if os.path.exists(self.salt_file):
            try:
                with open(self.salt_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read salt file: {e}")
                
        # Create new salt
        salt = os.urandom(16)
        try:
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            self._enforce_file_perms(self.salt_file)
        except Exception as e:
            logger.error(f"Failed to write salt file: {e}")
            
        return salt

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from device entropy + salt."""
        entropy = self._get_device_entropy()
        
        if CRYPTO_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(entropy))
            return key
        else:
            # Fallback simple derivation for itsdangerous/plaintext
            dk = hashlib.pbkdf2_hmac('sha256', entropy, salt, 100000)
            return base64.urlsafe_b64encode(dk)

    def store(self, token: str, is_expired: bool = False) -> bool:
        """Encrypt and persist token."""
        try:
            self._ensure_dir()
            salt = self._get_or_create_salt()
            key = self._derive_key(salt)
            
            data = {
                'stored_at': time.time(),
                'token': token,
                'is_expired': is_expired,
                'encryption': ENCRYPTION_METHOD
            }
            raw_data = json.dumps(data).encode('utf-8')
            
            if CRYPTO_AVAILABLE:
                f = Fernet(key)
                encrypted = f.encrypt(raw_data)
            elif 'itsdangerous' in ENCRYPTION_METHOD:
                # URLSafeSerializer doesn't encrypt, it just signs.
                # So we base64 the json, then sign it.
                s = URLSafeSerializer(key)
                encrypted = s.dumps(data).encode('utf-8')
            else:
                encrypted = base64.b64encode(raw_data)
                
            with open(self.session_file, 'wb') as f:
                f.write(encrypted)
                
            self._enforce_file_perms(self.session_file)
            return True
        except Exception as e:
            logger.error(f"Failed to store secret: {e}")
            return False

    def load_with_metadata(self) -> dict:
        """Load and decrypt full data dictionary."""
        if not os.path.exists(self.session_file):
            return None
            
        try:
            with open(self.session_file, 'rb') as f:
                encrypted = f.read()
                
            if not os.path.exists(self.salt_file):
                return None
                
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
                
            key = self._derive_key(salt)
            
            if CRYPTO_AVAILABLE:
                f = Fernet(key)
                raw_data = f.decrypt(encrypted)
                data = json.loads(raw_data.decode('utf-8'))
            elif 'itsdangerous' in ENCRYPTION_METHOD:
                s = URLSafeSerializer(key)
                data = s.loads(encrypted.decode('utf-8'))
            else:
                raw_data = base64.b64decode(encrypted)
                data = json.loads(raw_data.decode('utf-8'))
                
            return data
            
        except Exception:
            return None

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
        """Return metadata without the token."""
        meta = {
            'storage_secure': True,
            'encryption_method': ENCRYPTION_METHOD,
            'mode': SESSION_NOT_CONFIGURED,
            'stored_at': None
        }
        
        if not self.exists():
            return meta
            
        meta['mode'] = SESSION_PERSISTENT
        
        try:
            with open(self.session_file, 'rb') as f:
                encrypted = f.read()
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
                
            key = self._derive_key(salt)
            
            if CRYPTO_AVAILABLE:
                f = Fernet(key)
                raw_data = f.decrypt(encrypted)
                data = json.loads(raw_data.decode('utf-8'))
            elif 'itsdangerous' in ENCRYPTION_METHOD:
                s = URLSafeSerializer(key)
                data = s.loads(encrypted.decode('utf-8'))
            else:
                raw_data = base64.b64decode(encrypted)
                data = json.loads(raw_data.decode('utf-8'))
                
            meta['stored_at'] = data.get('stored_at')
        except Exception:
            meta['mode'] = SESSION_CORRUPTED
            
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
        """Returns actual session source mode constant."""
        if os.environ.get('RAPPI_BEARER_TOKEN'):
            return SESSION_EPHEMERAL
            
        if self._temp_token:
            return SESSION_TEMPORARY
            
        if self.store.exists():
            try:
                # Quick load test to see if it's corrupted
                if self.store.load_with_metadata() is None:
                    return SESSION_CORRUPTED
                return SESSION_PERSISTENT
            except Exception:
                return SESSION_CORRUPTED
                
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
            self.store.store(data['token'], is_expired=True)

"""
Crypto Service
Handles encryption and decryption of sensitive data like OAuth tokens
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class CryptoService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize crypto service
        
        Args:
            encryption_key: Base64-encoded encryption key. If not provided,
                          will try to get from environment or generate one.
        """
        if encryption_key:
            self.key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        else:
            # Try to get from environment
            env_key = os.getenv("ENCRYPTION_KEY")
            if env_key:
                self.key = env_key.encode() if isinstance(env_key, str) else env_key
            else:
                # Generate a key from a secret passphrase
                passphrase = os.getenv("ENCRYPTION_PASSPHRASE", "emailpilot-default-key-2024")
                salt = os.getenv("ENCRYPTION_SALT", "emailpilot-salt").encode()
                self.key = self._derive_key(passphrase, salt)
        
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """
        Derive an encryption key from a passphrase
        
        Args:
            passphrase: Secret passphrase
            salt: Salt for key derivation
            
        Returns:
            Base64-encoded encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string
        
        Args:
            data: Plain text to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            if not data:
                return ""
            
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted plain text
        """
        try:
            if not encrypted_data:
                return ""
            
            # Handle both base64-encoded and raw encrypted data
            try:
                decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            except Exception:
                decoded = encrypted_data.encode()
            
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt dictionary values
        
        Args:
            data: Dictionary with values to encrypt
            
        Returns:
            Dictionary with encrypted values
        """
        encrypted = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, str):
                    encrypted[key] = self.encrypt(value)
                else:
                    encrypted[key] = self.encrypt(str(value))
            else:
                encrypted[key] = None
        return encrypted
    
    def decrypt_dict(self, encrypted_data: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt dictionary values
        
        Args:
            encrypted_data: Dictionary with encrypted values
            
        Returns:
            Dictionary with decrypted values
        """
        decrypted = {}
        for key, value in encrypted_data.items():
            if value is not None:
                try:
                    decrypted[key] = self.decrypt(value)
                except Exception as e:
                    logger.warning(f"Failed to decrypt {key}: {e}")
                    decrypted[key] = None
            else:
                decrypted[key] = None
        return decrypted
    
    def hash_value(self, value: str) -> str:
        """
        Create a SHA256 hash of a value (for comparison without decryption)
        
        Args:
            value: Value to hash
            
        Returns:
            Hex-encoded hash string
        """
        return hashlib.sha256(value.encode()).hexdigest()
    
    def needs_refresh(
        self,
        expires_at: Optional[datetime],
        buffer_minutes: int = 5
    ) -> bool:
        """
        Check if a token needs refresh based on expiration
        
        Args:
            expires_at: Token expiration time
            buffer_minutes: Minutes before expiration to trigger refresh
            
        Returns:
            True if token needs refresh, False otherwise
        """
        if not expires_at:
            return False
        
        # Add buffer to refresh before actual expiration
        refresh_time = expires_at - timedelta(minutes=buffer_minutes)
        return datetime.utcnow() >= refresh_time


# Singleton instance for app-wide use
_crypto_service: Optional[CryptoService] = None


def get_crypto_service() -> CryptoService:
    """
    Get or create the singleton crypto service instance
    
    Returns:
        CryptoService instance
    """
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service
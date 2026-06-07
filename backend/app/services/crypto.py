"""Symmetric encryption for Tesla tokens at rest (build step 11).

Uses Fernet (AES-128-CBC + HMAC). The key comes from ``TOKEN_ENCRYPTION_KEY``.
If no key is configured we derive an *ephemeral* key so the app still boots in
development, but tokens encrypted that way will not survive a restart — a loud
warning is logged so this is never relied on in production.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet

from app.config import get_settings

log = logging.getLogger(__name__)

_settings = get_settings()


def _build_fernet() -> Fernet:
    key = _settings.token_encryption_key.strip()
    if not key:
        log.warning(
            "TOKEN_ENCRYPTION_KEY is not set; generating an EPHEMERAL key. "
            "Tokens will not be decryptable after a restart. Set a stable key "
            "in production."
        )
        key = Fernet.generate_key().decode()
    return Fernet(key.encode())


_fernet = _build_fernet()


def encrypt(plaintext: str) -> str:
    """Encrypt a string, returning a URL-safe base64 token."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`."""
    return _fernet.decrypt(token.encode()).decode()

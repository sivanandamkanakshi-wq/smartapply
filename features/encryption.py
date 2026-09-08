"""
Field-level encryption for SmartApply — encrypts sensitive profile fields
(Aadhaar number, PAN number, security answer) before they're stored in
SQLite, and decrypts them when read back.

SETUP:
1. Install the library:
       pip install cryptography
   (add "cryptography" to requirements.txt too)

2. Generate a secret key ONCE by running this in your terminal:
       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

   This prints something like:
       gAAAAABk...long-random-string...=

3. Add it to your .env file as a new line:
       ENCRYPTION_KEY=<the key you just generated>

   IMPORTANT: never commit this key to git, never share it, never
   regenerate it once you have real encrypted data saved — if you lose
   this key, or generate a new one, you will not be able to decrypt
   any Aadhaar/PAN/security-answer data already saved with the old key.

4. Save this file as features/encryption.py

5. In app.py, add near your other imports:
       from features.encryption import encrypt_field, decrypt_field
"""

import os
from cryptography.fernet import Fernet, InvalidToken

_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").strip()
_fernet = Fernet(_ENCRYPTION_KEY.encode()) if _ENCRYPTION_KEY else None


def encrypt_field(value):
    """Encrypts a string before saving to the database. Returns the
    original value unchanged if no ENCRYPTION_KEY is configured, or if
    the value is empty — so the app keeps working even before setup."""
    if not value:
        return value
    if not _fernet:
        print("[ENCRYPTION WARNING] ENCRYPTION_KEY not set — storing field unencrypted.")
        return value
    return _fernet.encrypt(value.encode()).decode()


def decrypt_field(value):
    """Decrypts a value read from the database. Returns the value
    unchanged if it isn't actually encrypted (e.g. old data saved before
    encryption was turned on, or no key configured) instead of crashing."""
    if not value:
        return value
    if not _fernet:
        return value
    try:
        return _fernet.decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        # Value wasn't encrypted (e.g. saved before this feature existed) —
        # return as-is rather than erroring out the whole page.
        return value
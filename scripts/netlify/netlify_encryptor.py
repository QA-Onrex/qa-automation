# scripts/netlify/netlify_encryptor.py
import os
import base64
import sys
import binascii
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# --- Configuration ---
PASSWORD_ENV = "REPORT_PASSWORD"
ITERATIONS = 100_000
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32  # AES-256 (32 bytes)

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a secure 256-bit key from password using PBKDF2."""
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        # --- TROUBLESHOOTING LOGGING ---
        print(f"[ENCRYPTOR:KEY] Derived Key (First 10 bytes HEX): {binascii.hexlify(key[:10]).decode()}")
        # ---
        return key
    except Exception as e:
        print(f"::error::Key derivation failed: {e}", file=sys.stderr)
        raise

def encrypt_bytes_to_bytes(data: bytes) -> bytes:
    """
    Encrypts given bytes in memory and returns encrypted bytes.
    Output format: STANDARD_BASE64(SALT + NONCE + CIPHERTEXT)
    """
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise ValueError(f"Environment variable {PASSWORD_ENV} not set")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    
    # --- TROUBLESHOOTING LOGGING ---
    print(f"[ENCRYPTOR:PARAMS] Salt (HEX): {binascii.hexlify(salt).decode()}")
    print(f"[ENCRYPTOR:PARAMS] Nonce (HEX): {binascii.hexlify(nonce).decode()}")
    # ---

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)

    # Use STANDARD Base64 encoding
    encrypted_data_b64 = base64.b64encode(salt + nonce + ciphertext)
    
    # --- TROUBLESHOOTING LOGGING ---
    print(f"[ENCRYPTOR:OUTPUT] Ciphertext+Tag Size: {len(ciphertext)}")
    print(f"[ENCRYPTOR:OUTPUT] Total Base64 Size: {len(encrypted_data_b64)} bytes")
    print(f"[ENCRYPTOR:OUTPUT] Base64 Start: {encrypted_data_b64[:50].decode()}...")
    # ---
    
    return encrypted_data_b64

def decrypt_file_to_bytes(encrypted_path: str) -> bytes:
    """Decrypts a file (containing STANDARD Base64) and returns original bytes."""
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise ValueError(f"Environment variable {PASSWORD_ENV} not set")
    
    # Read the file as raw bytes, matching how it was written
    with open(encrypted_path, "rb") as f:
        encrypted_data_b64 = f.read()
    
    # Perform standard Base64 decode
    encrypted_data = base64.b64decode(encrypted_data_b64)
    
    salt = encrypted_data[:SALT_SIZE]
    nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:]
    
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        # Better error handling for Python-side checks
        print(f"::error::[DECRYPTOR] AES-GCM check failed (Key/Tag Invalid): {e}", file=sys.stderr)
        raise ValueError("Decryption failed. Invalid password or tampered data.")


def encrypt_bytes_to_file(data: bytes, output_path: str):
    """Encrypts bytes and writes to file as raw Base64 bytes."""
    encrypted_data = encrypt_bytes_to_bytes(data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # CRITICAL: Write as raw bytes 'wb'
    with open(output_path, "wb") as f:
        f.write(encrypted_data)

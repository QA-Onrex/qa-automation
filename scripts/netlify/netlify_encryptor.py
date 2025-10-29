# scripts/netlify/netlify_encryptor.py
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# --- Configuration ---
PASSWORD_ENV = "REPORT_PASSWORD"
ITERATIONS = 100_000
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32  # AES-256

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a secure 256-bit key from password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_bytes_to_bytes(data: bytes) -> bytes:
    """
    Encrypts given bytes in memory and returns encrypted bytes.
    Output format: base64(SALT + NONCE + CIPHERTEXT)
    """
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise ValueError("Environment variable REPORT_PASSWORD not set")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)

    return base64.b64encode(salt + nonce + ciphertext)

def decrypt_bytes_to_bytes(encrypted_data: bytes) -> bytes:
    """Decrypts encrypted bytes and returns original bytes."""
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise ValueError("Environment variable REPORT_PASSWORD not set")

    encrypted_data = base64.b64decode(encrypted_data)
    
    salt = encrypted_data[:SALT_SIZE]
    nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:]

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

def encrypt_bytes_to_file(data: bytes, output_path: str):
    """Encrypts bytes and writes to file."""
    encrypted_data = encrypt_bytes_to_bytes(data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(encrypted_data)

def decrypt_file_to_bytes(encrypted_path: str) -> bytes:
    """Decrypts a file and returns original bytes."""
    with open(encrypted_path, "rb") as f:
        encrypted_data = f.read()
    return decrypt_bytes_to_bytes(encrypted_data)

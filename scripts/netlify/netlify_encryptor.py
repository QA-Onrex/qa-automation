# scripts/netlify/netlify_encryptor.py
import os
import base64
import sys
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# --- Configuration ---
PASSWORD_ENV = "REPORT_PASSWORD"
ITERATIONS = 100_000
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32  # AES-256 (256 bits)

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
        return kdf.derive(password.encode())
    except Exception as e:
        print(f"::error::Key derivation failed: {e}", file=sys.stderr)
        raise

def encrypt_bytes_to_bytes(data: bytes) -> bytes:
    """
    Encrypts given bytes in memory and returns encrypted bytes.
    Output format: URL_SAFE_BASE64(SALT + NONCE + CIPHERTEXT)
    """
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise ValueError(f"Environment variable {PASSWORD_ENV} not set")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    
    # --- Troubleshooting Output (Encryption) ---
    print(f"[ENCRYPTOR] Input Data Size: {len(data)} bytes")
    print(f"[ENCRYPTOR] Salt Size: {SALT_SIZE}, Nonce Size: {NONCE_SIZE}, Key Size: {KEY_SIZE}")
    # ---

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None) # None is AAD (Additional Authenticated Data)

    # Use URL-SAFE encoding for maximum browser compatibility
    encrypted_data_b64 = base64.urlsafe_b64encode(salt + nonce + ciphertext)
    
    # --- Troubleshooting Output (Encryption) ---
    print(f"[ENCRYPTOR] Ciphertext+Tag Size: {len(ciphertext)}")
    print(f"[ENCRYPTOR] Base64 Output Size: {len(encrypted_data_b64)} bytes")
    # ---
    
    return encrypted_data_b64

def decrypt_bytes_to_bytes(encrypted_data_b64: bytes) -> bytes:
    """Decrypts encrypted URL_SAFE_BASE64 bytes and returns original bytes."""
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise ValueError(f"Environment variable {PASSWORD_ENV} not set")
    
    try:
        # Use URL-SAFE decoding
        encrypted_data = base64.urlsafe_b64decode(encrypted_data_b64)
    except Exception as e:
        print(f"::error::[DECRYPTOR] Base64 decoding failed: {e}", file=sys.stderr)
        raise ValueError("Invalid Base64 format.")

    if len(encrypted_data) < SALT_SIZE + NONCE_SIZE:
        print(f"::error::[DECRYPTOR] Data too short. Expected min {SALT_SIZE + NONCE_SIZE} bytes.", file=sys.stderr)
        raise ValueError("Encrypted data is truncated or corrupt.")

    salt = encrypted_data[:SALT_SIZE]
    nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:]

    # --- Troubleshooting Output (Decryption) ---
    print(f"[DECRYPTOR] Salt Size: {len(salt)}, Nonce Size: {len(nonce)}, Ciphertext Size: {len(ciphertext)}")
    # ---
    
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        print(f"::error::[DECRYPTOR] AES-GCM Decryption failed (Authentication Tag or Key Invalid): {e}", file=sys.stderr)
        # This is the standard exception for bad key/password or tampered data
        raise ValueError("Decryption failed. Invalid password or tampered data.")


def encrypt_bytes_to_file(data: bytes, output_path: str):
    """Encrypts bytes and writes to file as a string (URL-Safe Base64)."""
    encrypted_data_b64 = encrypt_bytes_to_bytes(data) # Base64 BYTES
    
    # Decode to a clean ASCII string for writing to disk in text mode
    encrypted_data_str = encrypted_data_b64.decode('ascii')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Write as a string to prevent BOMs or other byte issues
    with open(output_path, "w", encoding="ascii") as f:
        f.write(encrypted_data_str)

def decrypt_file_to_bytes(encrypted_path: str) -> bytes:
    """Decrypts a file (containing URL-Safe Base64 string) and returns original bytes."""
    # Read the content as a string
    with open(encrypted_path, "r", encoding="ascii") as f:
        encrypted_data_str = f.read()
    
    # Encode back to bytes before passing to the helper
    encrypted_data_b64 = encrypted_data_str.encode('ascii')
    
    return decrypt_bytes_to_bytes(encrypted_data_b64)

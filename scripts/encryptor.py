# scripts/encryptor.py
"""
encryptor.py — AES-256-GCM file/bytes encryption utilities.

Usage:
    from scripts.encryptor import encrypt_file, decrypt_file_to_bytes, encrypt_data, decrypt_data

Dependencies:
    pip install cryptography
"""

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import typing

# --- Configurable parameters ---
SALT_SIZE = 16      # bytes
NONCE_SIZE = 12     # bytes (recommended for AESGCM)
KDF_ITERATIONS = 200_000  # PBKDF2 iterations (reasonable default)
KEY_SIZE = 32       # bytes for AES-256


# --- Internal helpers -------------------------------------------------------
def _derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 32-byte key from password and salt using PBKDF2-HMAC-SHA256.
    """
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    if not isinstance(salt, (bytes, bytearray)) or len(salt) < 8:
        raise ValueError("salt must be bytes and at least 8 bytes long")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def _pack_encrypted(salt: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """
    Format: salt||nonce||ciphertext
    """
    return salt + nonce + ciphertext


def _unpack_encrypted(blob: bytes) -> typing.Tuple[bytes, bytes, bytes]:
    """
    Reverse of _pack_encrypted. Returns (salt, nonce, ciphertext).
    """
    if len(blob) < SALT_SIZE + NONCE_SIZE + 1:
        raise ValueError("Encrypted blob too small or corrupted")
    salt = blob[:SALT_SIZE]
    nonce = blob[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = blob[SALT_SIZE + NONCE_SIZE:]
    return salt, nonce, ciphertext


# --- Public API: data (bytes) -----------------------------------------------
def encrypt_data(plaintext: bytes, password: str) -> bytes:
    """
    Encrypt bytes using AES-256-GCM with a PBKDF2-derived key.
    Returns raw binary: salt||nonce||ciphertext
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext must be bytes")
    if not password:
        raise ValueError("password must not be empty")

    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    ct = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return _pack_encrypted(salt, nonce, ct)


def decrypt_data(enc_blob: bytes, password: str) -> bytes:
    """
    Decrypt bytes previously produced by encrypt_data.
    Input is raw: salt||nonce||ciphertext
    Returns plaintext bytes.
    """
    if not isinstance(enc_blob, (bytes, bytearray)):
        raise TypeError("enc_blob must be bytes")
    if not password:
        raise ValueError("password must not be empty")

    salt, nonce, ciphertext = _unpack_encrypted(enc_blob)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)


# --- Public API: files -----------------------------------------------------
def encrypt_file(in_path: str, password: str, out_path: typing.Optional[str] = None, remove_original: bool = False) -> str:
    """
    Encrypt a file on disk.

    - in_path: path to plaintext file (read in binary)
    - password: encryption password
    - out_path: optional path for encrypted output. If omitted, writes in_path + '.enc'
    - remove_original: if True, delete the plaintext input after successful encryption

    Returns the path to the encrypted file.
    """
    if not os.path.isfile(in_path):
        raise FileNotFoundError(f"{in_path} not found")

    if out_path is None:
        out_path = in_path + ".enc"

    # Read source
    with open(in_path, "rb") as f:
        data = f.read()

    enc = encrypt_data(data, password)

    # Write atomically to temporary file then replace
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(enc)
    os.replace(tmp_path, out_path)

    if remove_original:
        try:
            os.remove(in_path)
        except Exception:
            pass

    return out_path


def decrypt_file_to_bytes(enc_path: str, password: str) -> bytes:
    """
    Decrypt an encrypted file and return plaintext bytes.
    """
    if not os.path.isfile(enc_path):
        raise FileNotFoundError(f"{enc_path} not found")
    with open(enc_path, "rb") as f:
        enc_blob = f.read()
    return decrypt_data(enc_blob, password)


def decrypt_file_to_path(enc_path: str, password: str, out_path: str, remove_encrypted: bool = False) -> str:
    """
    Decrypt an encrypted file and write plaintext to out_path. Returns out_path.
    If remove_encrypted is True, the encrypted file will be removed after successful decryption.
    """
    plaintext = decrypt_file_to_bytes(enc_path, password)
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(plaintext)
    os.replace(tmp_path, out_path)
    if remove_encrypted:
        try:
            os.remove(enc_path)
        except Exception:
            pass
    return out_path


# --- Utility helpers -------------------------------------------------------
def is_encrypted_filename(path: str) -> bool:
    """
    Simple helper: treat files with .enc extension as encrypted.
    """
    return str(path).lower().endswith(".enc")


def safe_remove(path: str):
    try:
        os.remove(path)
    except Exception:
        pass


# --- Example convenience flows ---------------------------------------------
def encrypt_and_replace(in_path: str, password: str):
    """
    Convenience: encrypt file and replace the original with the .enc file.
    (Equivalent to encrypt_file(in_path, password, out_path=in_path+'.enc', remove_original=True))
    """
    enc_path = encrypt_file(in_path, password, out_path=in_path + ".enc", remove_original=True)
    return enc_path


# --- If run as script, simple demo (not executed in Actions) ----------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple encrypt/decrypt helper (AES-256-GCM + PBKDF2).")
    parser.add_argument("mode", choices=["enc", "dec"], help="enc=encrypt file, dec=decrypt file")
    parser.add_argument("input", help="input file path")
    parser.add_argument("--out", "-o", help="output file path (optional)")
    parser.add_argument("--pw", "-p", help="password (if omitted, read REPORT_PASSWORD env var)")
    parser.add_argument("--remove", action="store_true", help="remove original after encrypt/decrypt")
    args = parser.parse_args()

    pw = args.pw or os.getenv("REPORT_PASSWORD")
    if not pw:
        raise SystemExit("No password provided via --pw or REPORT_PASSWORD env var.")

    if args.mode == "enc":
        out = args.out or args.input + ".enc"
        print(f"Encrypting {args.input} -> {out}")
        encrypt_file(args.input, pw, out, remove_original=args.remove)
        print("Done.")
    else:
        out = args.out or args.input.replace(".enc", ".dec")
        print(f"Decrypting {args.input} -> {out}")
        decrypt_file_to_path(args.input, pw, out, remove_encrypted=args.remove)
        print("Done.")


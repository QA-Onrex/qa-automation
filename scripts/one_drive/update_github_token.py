# scripts/one_drive/update_github_token.py (FIXED ENCRYPTION)
import os
import requests
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_public_key

def encrypt_github_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a secret using GitHub's public key - FIXED VERSION"""
    try:
        # Clean the public key - handle different formats
        if "-----BEGIN" not in public_key:
            public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
        else:
            # Ensure proper formatting
            public_key = public_key.strip()
            
        # Load the public key
        key = load_pem_public_key(public_key.encode(), backend=default_backend())
        
        # Encrypt the secret
        encrypted = key.encrypt(
            secret_value.encode('utf-8'),
            padding.PKCS1v15()
        )
        
        return base64.b64encode(encrypted).decode('utf-8')
        
    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        print(f"💡 Public key preview: {public_key[:100]}...")
        return None

def update_github_secret(secret_name: str, secret_value: str) -> bool:
    """Update GitHub secret - FIXED VERSION"""
    repo = os.getenv('GITHUB_REPOSITORY')
    token = os.getenv('GITHUB_TOKEN')
    
    if not all([repo, token]):
        print("❌ Missing GitHub environment variables")
        return False
    
    # Get public key with better error handling
    pubkey_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        pubkey_response = requests.get(pubkey_url, headers=headers)
        if pubkey_response.status_code != 200:
            print(f"❌ Failed to get public key: {pubkey_response.status_code}")
            print(f"💡 Response: {pubkey_response.text}")
            return False
        
        pubkey_data = pubkey_response.json()
        key_id = pubkey_data['key_id']
        public_key = pubkey_data['key']
        
        print(f"🔑 Retrieved public key: {key_id}")
        
    except Exception as e:
        print(f"❌ Error getting public key: {e}")
        return False
    
    # Encrypt and update
    encrypted_secret = encrypt_github_secret(public_key, secret_value)
    if not encrypted_secret:
        return False
    
    secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    data = {
        'encrypted_value': encrypted_secret,
        'key_id': key_id
    }
    
    try:
        response = requests.put(secret_url, headers=headers, json=data)
        if response.status_code == 204:
            print(f"✅ Successfully updated {secret_name}")
            return True
        else:
            print(f"❌ Failed to update secret: {response.status_code}")
            print(f"💡 Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating secret: {e}")
        return False

# ... rest of your existing functions (refresh_onedrive_token, main) remain the same ...

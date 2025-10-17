# scripts/one_drive/update_github_token.py
import os
import requests
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_public_key

def encrypt_github_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a secret using GitHub's public key"""
    try:
        public_key = public_key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").strip()
        public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
        
        key = load_pem_public_key(public_key.encode(), backend=default_backend())
        encrypted = key.encrypt(secret_value.encode(), padding.PKCS1v15())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        print(f"::error::Failed to encrypt secret: {e}")
        return None

def update_github_secret(secret_name: str, secret_value: str) -> bool:
    """Update GitHub secret using auto-injected GitHub variables"""
    # These are automatically provided by GitHub Actions
    repo = os.getenv('GITHUB_REPOSITORY')  # Auto-injected
    token = os.getenv('GITHUB_TOKEN')      # Auto-injected
    
    if not all([repo, token]):
        print("❌ Missing auto-injected GitHub variables")
        return False
    
    # Get public key
    pubkey_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    pubkey_response = requests.get(pubkey_url, headers=headers)
    if pubkey_response.status_code != 200:
        print(f"❌ Failed to get public key: {pubkey_response.status_code}")
        return False
    
    pubkey_data = pubkey_response.json()
    key_id = pubkey_data['key_id']
    public_key = pubkey_data['key']
    
    # Encrypt and update
    encrypted_secret = encrypt_github_secret(public_key, secret_value)
    if not encrypted_secret:
        return False
    
    secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    data = {
        'encrypted_value': encrypted_secret,
        'key_id': key_id
    }
    
    response = requests.put(secret_url, headers=headers, json=data)
    if response.status_code == 204:
        print(f"✅ Successfully updated {secret_name}")
        return True
    else:
        print(f"❌ Failed to update secret: {response.status_code}")
        return False

def main():
    """Main function for token refresh during automation"""
    print("🔄 Checking for token refresh in automation...")
    
    # This would be called from the main automation workflow
    # For now, it's a placeholder that will be used by the main fetch workflow
    print("📝 This script is called by the main automation workflow")
    print("💡 It will refresh tokens during the daily automation run")

if __name__ == "__main__":
    main()

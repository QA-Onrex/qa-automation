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

def refresh_onedrive_token():
    """Refresh OneDrive token and return new refresh token"""
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("ONEDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("❌ Missing OneDrive credentials for token refresh")
        return None
    
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'https://graph.microsoft.com/Files.ReadWrite offline_access'
    }
    
    print("🔄 Refreshing OneDrive token...")
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        new_refresh_token = tokens.get('refresh_token')
        
        if new_refresh_token and new_refresh_token != refresh_token:
            print("✅ Successfully refreshed OneDrive token")
            return new_refresh_token
        else:
            print("ℹ️ Token refresh succeeded but no new refresh token returned")
            return refresh_token  # Return original if no new one
    else:
        print(f"❌ Token refresh failed: {response.status_code}")
        print(f"Error: {response.text}")
        return None

def main():
    """Main function for token refresh during automation"""
    print("🔄 Checking for OneDrive token refresh...")
    
    # Refresh the OneDrive token
    new_refresh_token = refresh_onedrive_token()
    
    if new_refresh_token:
        print("💾 Updating GitHub secret with new refresh token...")
        if update_github_secret("ONEDRIVE_REFRESH_TOKEN", new_refresh_token):
            print("🎉 GitHub secret updated successfully!")
            print("🔧 OneDrive token will remain valid for another 90 days")
        else:
            print("❌ Failed to update GitHub secret")
            print("💡 The current token will still work, but may expire eventually")
    else:
        print("⚠️ Could not refresh token, but current token may still be valid")
        print("💡 If you see repeated failures, run the manual token setup workflow")

if __name__ == "__main__":
    main()

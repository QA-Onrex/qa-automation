# scripts/one_drive/manage_onedrive_token.py
import requests
import os
import sys

# Add the scripts directory to path so we can import other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from one_drive/update_github_token import update_github_secret

def get_new_token_via_browser():
    """Get initial token via browser OAuth flow"""
    tenant_id = os.getenv("ONEDRIVE_TENANT_ID")
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    
    scope = "https://graph.microsoft.com/Files.ReadWrite"
    auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?client_id={client_id}&scope={scope}&response_type=code&redirect_uri=http://localhost:8080&response_mode=query"

    print("🚀 INITIAL SETUP: No valid token found")
    print("🔗 Visit this URL in your browser:")
    print(auth_url)
    print("\n📋 After logging in, copy the 'code' parameter from the URL bar")
    print("   (looks like: code=OAQABAAIAAA...)\n")
    
    auth_code = input("Paste the authorization code here: ").strip()

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'code': auth_code,
        'redirect_uri': 'http://localhost:8080',
        'grant_type': 'authorization_code',
        'scope': scope
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get('refresh_token')
    else:
        raise Exception(f"Failed to get token: {response.status_code} - {response.text}")

def refresh_existing_token():
    """Refresh existing token using refresh token flow"""
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("ONEDRIVE_REFRESH_TOKEN")
    tenant_id = os.getenv("ONEDRIVE_TENANT_ID")
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'https://graph.microsoft.com/Files.ReadWrite'
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get('refresh_token')
    else:
        print(f"❌ Token refresh failed: {response.status_code}")
        return None

def main():
    print("🔑 OneDrive Token Manager")
    print("=" * 40)
    
    # Check if we have existing credentials
    existing_token = os.getenv("ONEDRIVE_REFRESH_TOKEN", "").strip()
    has_valid_token = existing_token and len(existing_token) > 10  # Basic validation
    
    if has_valid_token:
        print("🔄 Attempting to refresh existing token...")
        new_token = refresh_existing_token()
        
        if new_token:
            print("✅ Successfully refreshed token")
        else:
            print("🔄 Refresh failed, falling back to initial setup...")
            new_token = get_new_token_via_browser()
    else:
        print("🚀 No valid token found - starting initial setup...")
        new_token = get_new_token_via_browser()
    
    # Update GitHub secret
    if new_token:
        print("💾 Saving token to GitHub Secrets...")
        if update_github_secret("ONEDRIVE_REFRESH_TOKEN", new_token):
            print("🎉 Token successfully saved to GitHub Secrets!")
            print("🔧 The token will now auto-refresh in daily workflows")
        else:
            print("❌ Failed to save token to GitHub Secrets")
            print("💡 Manual step: Copy this token to ONEDRIVE_REFRESH_TOKEN secret:")
            print(new_token)
    else:
        print("❌ Failed to obtain token")

if __name__ == "__main__":
    main()

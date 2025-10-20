
# scripts/one_drive/onedrive_process_attachments.py
import os
import zipfile
import io
import traceback
import requests
from urllib.parse import quote

# OneDrive folder paths
ONEDRIVE_ATTACHMENTS_FOLDER = "qa-automation/attachments"
ONEDRIVE_HTML_FOLDER = "qa-automation/html"

def get_onedrive_access_token():
    """Get access token using refresh token"""
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("ONEDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise Exception("OneDrive credentials missing")
    
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'https://graph.microsoft.com/Files.ReadWrite offline_access'
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get('access_token')
    else:
        raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

def download_from_onedrive_to_memory(file_path, access_token):
    """Download a file from OneDrive directly to memory"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/content"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        print(f"❌ Failed to download {file_path}: {response.status_code}")
        return None

def upload_to_onedrive_from_memory(file_content, file_path, access_token):
    """Upload a file to OneDrive directly from memory"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/content"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream'
    }
    
    response = requests.put(url, headers=headers, data=file_content)
    return response.status_code in [200, 201]

def delete_from_onedrive(file_path, access_token):
    """Delete a file from OneDrive"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.delete(url, headers=headers)
    return response.status_code in [200, 204]

def list_onedrive_files(folder_path, access_token):
    """List files in a OneDrive folder"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(folder_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/children"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        items = response.json().get('value', [])
        return [item['name'] for item in items if 'file' in item]
    else:
        print(f"❌ Failed to list files in {folder_path}: {response.status_code}")
        return []

def extract_html_from_zip_in_memory(zip_bytes, original_zip_name):
    """Extract the first HTML file from ZIP bytes in memory"""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            html_files = [f for f in z.namelist() if f.lower().endswith(".html")]
            if not html_files:
                print(f"⚠️ No HTML file found in {original_zip_name}")
                return None

            html_file_in_zip = html_files[0]
            html_filename = os.path.splitext(os.path.basename(original_zip_name))[0] + ".html"

            # Read HTML bytes from ZIP in memory
            with z.open(html_file_in_zip) as src:
                html_bytes = src.read()

            print(f"✅ Extracted {html_filename} from {original_zip_name}")
            return html_filename, html_bytes

    except Exception as e:
        print(f"❌ Failed to process {original_zip_name}: {e}")
        traceback.print_exc()
        return None

def main():
    print("🔄 Processing OneDrive attachments in memory...")
    
    try:
        # Get OneDrive access token
        access_token = get_onedrive_access_token()
                
        # List ZIP files in attachments folder
        zip_files = [f for f in list_onedrive_files(ONEDRIVE_ATTACHMENTS_FOLDER, access_token) 
                    if f.lower().endswith(".zip")]
        
        if not zip_files:
            print("ℹ️ No ZIP files to process in OneDrive attachments folder")
            return

        print(f"📦 Found {len(zip_files)} ZIP files to process")
        
        processed_count = 0
        for zip_file in zip_files:
            try:
                print(f"🔍 Processing {zip_file}...")
                
                # Download ZIP from OneDrive directly to memory
                zip_path = f"{ONEDRIVE_ATTACHMENTS_FOLDER}/{zip_file}"
                zip_bytes = download_from_onedrive_to_memory(zip_path, access_token)
                
                if not zip_bytes:
                    continue
                
                # Extract HTML from ZIP in memory
                result = extract_html_from_zip_in_memory(zip_bytes, zip_file)
                if not result:
                    continue
                    
                html_filename, html_bytes = result
                
                # Upload HTML to OneDrive directly from memory
                html_path = f"{ONEDRIVE_HTML_FOLDER}/{html_filename}"
                if upload_to_onedrive_from_memory(html_bytes, html_path, access_token):
                    print(f"✅ Uploaded {html_filename} to OneDrive")
                    
                    # Delete original ZIP from OneDrive
                    if delete_from_onedrive(zip_path, access_token):
                        print(f"🗑️ Deleted {zip_file} from OneDrive")
                        processed_count += 1
                    else:
                        print(f"⚠️ Failed to delete {zip_file}")
                else:
                    print(f"❌ Failed to upload {html_filename}")
                    
            except Exception as e:
                print(f"❌ Error processing {zip_file}: {e}")
                traceback.print_exc()
        
        print(f"🎉 Processed {processed_count} out of {len(zip_files)} ZIP files")
        
    except Exception as e:
        print(f"❌ OneDrive processing failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

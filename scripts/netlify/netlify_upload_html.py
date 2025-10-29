# scripts/netlify/netlify_upload_html.py
import os
import requests
import json
import traceback
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Netlify API configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

def create_netlify_deploy(site_id, auth_token, file_paths):
    """Create a new deploy with files on Netlify."""
    try:
        # Step 1: Create a new deploy
        deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Create empty deploy
        deploy_response = requests.post(deploy_url, headers=headers, json={})
        if deploy_response.status_code != 200:
            print(f"::error::Failed to create deploy: {deploy_response.status_code} - {deploy_response.text}")
            return None
            
        deploy_data = deploy_response.json()
        deploy_id = deploy_data['id']
        print(f"::notice::Created deploy: {deploy_id}")
        
        # Step 2: Upload files to the deploy
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            upload_url = f"{NETLIFY_API_BASE}/deploys/{deploy_id}/files/{filename}"
            
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            upload_headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/octet-stream"
            }
            
            upload_response = requests.put(upload_url, headers=upload_headers, data=file_content)
            if upload_response.status_code == 200:
                print(f"::notice::Uploaded {filename} to deploy")
            else:
                print(f"::error::Failed to upload {filename}: {upload_response.status_code} - {upload_response.text}")
        
        # Step 3: Publish the deploy
        publish_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys/{deploy_id}/restore"
        publish_response = requests.post(publish_url, headers=headers)
        
        if publish_response.status_code == 200:
            print(f"::notice::Deploy published successfully")
            return f"https://{site_id}.netlify.app/{filename}"
        else:
            print(f"::error::Failed to publish deploy: {publish_response.status_code} - {publish_response.text}")
            return None
            
    except Exception as e:
        print(f"::error::Error in deploy process: {e}")
        traceback.print_exc()
        return None

def upload_file_simple(site_id, auth_token, file_path):
    """Simple file upload using Netlify's file API."""
    try:
        filename = os.path.basename(file_path)
        
        # Read the encrypted file
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # Upload to Netlify
        upload_url = f"https://api.netlify.com/api/v1/sites/{site_id}/files/{filename}"
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/octet-stream"
        }
        
        print(f"::notice::Uploading {filename} to Netlify...")
        response = requests.put(upload_url, headers=headers, data=file_content)
        
        if response.status_code in [200, 201]:
            file_url = f"https://{site_id}.netlify.app/{filename}"
            print(f"::notice::Successfully uploaded {filename} to {file_url}")
            return file_url
        else:
            print(f"::error::Failed to upload {filename}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"::error::Error uploading {file_path}: {e}")
        traceback.print_exc()
        return None

def load_existing_urls():
    """Load existing URLs from file."""
    if os.path.exists(URLS_FILE):
        try:
            with open(URLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_urls(urls_dict):
    """Save URLs to file."""
    os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls_dict, f, indent=2, ensure_ascii=False)

def verify_upload(file_url):
    """Verify that the uploaded file is accessible."""
    try:
        response = requests.get(file_url, timeout=10)
        if response.status_code == 200:
            print(f"::notice::Verified: {file_url} is accessible")
            return True
        else:
            print(f"::warning::File not accessible: {file_url} - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"::warning::Could not verify {file_url}: {e}")
        return False

def main():
    if not NETLIFY_SITE_ID or not NETLIFY_AUTH_TOKEN:
        print("::error::NETLIFY_SITE_ID or NETLIFY_AUTH_TOKEN not set")
        return

    html_files = [f for f in os.listdir(HTML_FOLDER) if f.lower().endswith(".html")]
    if not html_files:
        print("::notice::No HTML files to upload to Netlify.")
        return

    # Load existing URLs
    urls = load_existing_urls()
    uploaded_count = 0

    for html_file in html_files:
        html_path = os.path.join(HTML_FOLDER, html_file)
        
        # Upload to Netlify using simple method
        file_url = upload_file_simple(NETLIFY_SITE_ID, NETLIFY_AUTH_TOKEN, html_path)
        
        if file_url:
            # Verify the upload is accessible
            if verify_upload(file_url):
                # Store the URL mapping
                urls[html_file] = file_url
                uploaded_count += 1
                
                # Delete local HTML file after successful upload
                os.remove(html_path)
                print(f"::notice::Deleted local file {html_file} after successful Netlify upload")
            else:
                print(f"::warning::Upload verification failed for {html_file}, keeping local copy")
        else:
            print(f"::warning::Failed to upload {html_file}, keeping local copy")

    # Save updated URLs
    save_urls(urls)
    print(f"::notice::Uploaded {uploaded_count} files to Netlify and updated URL mappings.")

if __name__ == "__main__":
    main()

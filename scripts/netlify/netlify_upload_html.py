# scripts/netlify/netlify_upload_html.py
import os
import requests
import json
import traceback
import sys
import hashlib
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Netlify API configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

def upload_files_to_netlify(site_id, auth_token, file_paths):
    """Upload files to Netlify using the deploy API."""
    try:
        # Step 1: Get current site deploy
        site_url = f"{NETLIFY_API_BASE}/sites/{site_id}"
        headers = {
            "Authorization": f"Bearer {auth_token}",
        }
        
        print(f"::notice::Getting site information...")
        site_response = requests.get(site_url, headers=headers)
        if site_response.status_code != 200:
            print(f"::error::Failed to get site info: {site_response.status_code} - {site_response.text}")
            return None
            
        site_data = site_response.json()
        print(f"::notice::Site: {site_data.get('name')} - {site_data.get('url')}")
        
        # Step 2: Create a new deploy with files
        deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        
        # Prepare files data
        files_data = {}
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Netlify expects files in a specific format
            files_data[filename] = file_content.hex()
        
        deploy_payload = {
            "files": files_data,
            "draft": False
        }
        
        print(f"::notice::Creating deploy with {len(file_paths)} files...")
        deploy_response = requests.post(deploy_url, headers=headers, json=deploy_payload)
        
        if deploy_response.status_code == 200:
            deploy_data = deploy_response.json()
            deploy_id = deploy_data['id']
            deploy_url = deploy_data['url']
            print(f"::notice::Deploy created: {deploy_id}")
            print(f"::notice::Deploy URL: {deploy_url}")
            
            # Wait for deploy to be ready
            print(f"::notice::Waiting for deploy to process...")
            time.sleep(10)
            
            # Return URLs for each file
            file_urls = {}
            for file_path in file_paths:
                filename = os.path.basename(file_path)
                file_url = f"https://{site_id}.netlify.app/{filename}"
                file_urls[filename] = file_url
            
            return file_urls
        else:
            print(f"::error::Failed to create deploy: {deploy_response.status_code} - {deploy_response.text}")
            return None
            
    except Exception as e:
        print(f"::error::Error in deploy process: {e}")
        traceback.print_exc()
        return None

def upload_files_alternative(site_id, auth_token, file_paths):
    """Alternative method using Netlify's file upload with proper API."""
    try:
        # This method uses the correct Netlify API for file uploads
        deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        headers = {
            "Authorization": f"Bearer {auth_token}",
        }
        
        # First, get the latest deploy to build upon
        site_deploys_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        deploys_response = requests.get(site_deploys_url, headers=headers)
        
        if deploys_response.status_code != 200:
            print(f"::error::Failed to get site deploys: {deploys_response.text}")
            return None
        
        deploys = deploys_response.json()
        if not deploys:
            print(f"::error::No existing deploys found for site")
            return None
        
        latest_deploy = deploys[0]
        latest_deploy_id = latest_deploy['id']
        
        print(f"::notice::Building upon deploy: {latest_deploy_id}")
        
        # Create a new deploy based on the latest one
        deploy_payload = {
            "deploy_id": latest_deploy_id
        }
        
        deploy_response = requests.post(deploy_url, headers=headers, json=deploy_payload)
        if deploy_response.status_code != 200:
            print(f"::error::Failed to create new deploy: {deploy_response.text}")
            return None
        
        new_deploy = deploy_response.json()
        new_deploy_id = new_deploy['id']
        
        print(f"::notice::Created new deploy: {new_deploy_id}")
        
        # Upload files to the new deploy
        file_urls = {}
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            upload_url = f"{NETLIFY_API_BASE}/deploys/{new_deploy_id}/files/{filename}"
            
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            upload_response = requests.put(upload_url, headers=headers, data=file_content)
            if upload_response.status_code == 200:
                file_url = f"https://{site_id}.netlify.app/{filename}"
                file_urls[filename] = file_url
                print(f"::notice::Uploaded {filename}")
            else:
                print(f"::error::Failed to upload {filename}: {upload_response.status_code} - {upload_response.text}")
        
        # Publish the deploy
        publish_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys/{new_deploy_id}/restore"
        publish_response = requests.post(publish_url, headers=headers)
        
        if publish_response.status_code == 200:
            print(f"::notice::Deploy published successfully")
            return file_urls
        else:
            print(f"::error::Failed to publish deploy: {publish_response.text}")
            return None
            
    except Exception as e:
        print(f"::error::Error in alternative upload: {e}")
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
    
    # Prepare file paths
    file_paths = [os.path.join(HTML_FOLDER, f) for f in html_files]
    
    # Try alternative upload method
    print(f"::notice::Uploading {len(file_paths)} files to Netlify...")
    file_urls = upload_files_alternative(NETLIFY_SITE_ID, NETLIFY_AUTH_TOKEN, file_paths)
    
    if file_urls:
        # Update URLs and clean up
        for filename, file_url in file_urls.items():
            urls[filename] = file_url
            
            # Delete local file after successful upload
            local_path = os.path.join(HTML_FOLDER, filename)
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"::notice::Deleted local file {filename}")
        
        # Save updated URLs
        save_urls(urls)
        print(f"::notice::Successfully uploaded {len(file_urls)} files to Netlify")
    else:
        print(f"::error::Failed to upload files to Netlify")

if __name__ == "__main__":
    main()

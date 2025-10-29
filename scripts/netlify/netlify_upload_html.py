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

def wait_for_deploy_ready(site_id, auth_token, deploy_id, max_wait=60):
    """Wait for deploy to be ready."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys/{deploy_id}"
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(deploy_url, headers=headers)
        if response.status_code == 200:
            deploy_data = response.json()
            state = deploy_data.get('state', '')
            print(f"::notice::Deploy state: {state}")
            
            if state == 'ready':
                return True
            elif state == 'error':
                print(f"::error::Deploy failed: {deploy_data}")
                return False
        time.sleep(5)
    
    print(f"::error::Deploy timeout after {max_wait} seconds")
    return False

def upload_files_to_netlify(site_id, auth_token, file_paths):
    """Upload files to Netlify using the correct deploy workflow."""
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Step 1: Get the latest production deploy
        site_url = f"{NETLIFY_API_BASE}/sites/{site_id}"
        site_response = requests.get(site_url, headers=headers)
        if site_response.status_code != 200:
            print(f"::error::Failed to get site: {site_response.text}")
            return None
        
        site_data = site_response.json()
        production_deploy_id = site_data.get('published_deploy', {}).get('id')
        
        if not production_deploy_id:
            print(f"::error::No production deploy found")
            return None
        
        print(f"::notice::Production deploy ID: {production_deploy_id}")
        
        # Step 2: Create a new deploy based on production
        deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        deploy_payload = {
            "deploy_id": production_deploy_id
        }
        
        print(f"::notice::Creating new deploy...")
        deploy_response = requests.post(deploy_url, headers=headers, json=deploy_payload)
        if deploy_response.status_code != 200:
            print(f"::error::Failed to create deploy: {deploy_response.text}")
            return None
        
        new_deploy = deploy_response.json()
        new_deploy_id = new_deploy['id']
        print(f"::notice::Created deploy: {new_deploy_id}")
        
        # Step 3: Upload files to the new deploy
        file_urls = {}
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            upload_url = f"{NETLIFY_API_BASE}/deploys/{new_deploy_id}/files/{filename}"
            
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            print(f"::notice::Uploading {filename}...")
            upload_response = requests.put(upload_url, headers=headers, data=file_content)
            
            if upload_response.status_code == 200:
                file_url = f"https://{site_id}.netlify.app/{filename}"
                file_urls[filename] = file_url
                print(f"::notice::Uploaded {filename}")
            else:
                print(f"::error::Failed to upload {filename}: {upload_response.status_code} - {upload_response.text}")
        
        # Step 4: Wait for deploy to be ready
        print(f"::notice::Waiting for deploy to process...")
        if wait_for_deploy_ready(site_id, auth_token, new_deploy_id):
            # Step 5: Publish the deploy
            publish_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys/{new_deploy_id}/publish"
            publish_response = requests.post(publish_url, headers=headers)
            
            if publish_response.status_code == 200:
                print(f"::notice::Deploy published successfully")
                return file_urls
            else:
                print(f"::error::Failed to publish deploy: {publish_response.text}")
                return None
        else:
            print(f"::error::Deploy never became ready")
            return None
            
    except Exception as e:
        print(f"::error::Error in upload process: {e}")
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
    
    print(f"::notice::Uploading {len(file_paths)} files to Netlify...")
    file_urls = upload_files_to_netlify(NETLIFY_SITE_ID, NETLIFY_AUTH_TOKEN, file_paths)
    
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
        
        # Verify uploads
        print(f"::notice::Verifying uploads...")
        for filename, file_url in file_urls.items():
            try:
                response = requests.head(file_url, timeout=10)
                if response.status_code == 200:
                    print(f"::notice::✓ {filename} is accessible")
                else:
                    print(f"::warning::✗ {filename} returned {response.status_code}")
            except Exception as e:
                print(f"::warning::Could not verify {filename}: {e}")
    else:
        print(f"::error::Failed to upload files to Netlify")
        # Don't delete local files if upload failed
        print(f"::notice::Keeping local files for retry")

if __name__ == "__main__":
    main()

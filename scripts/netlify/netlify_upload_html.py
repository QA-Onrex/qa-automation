# scripts/netlify/netlify_upload_html.py
import os
import requests
import json
import traceback
import sys
import time
import base64
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Netlify API configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

def create_deploy_with_files(site_id, auth_token, files_dict):
    """Create a proper Netlify deploy with files and wait for completion."""
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Step 1: Create a new deploy
        deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        
        # Prepare files in the format Netlify expects
        deploy_files = {}
        for filename, file_path in files_dict.items():
            with open(file_path, "rb") as f:
                file_content = f.read()
            # Netlify expects files as hex strings
            deploy_files[filename] = file_content.hex()
        
        deploy_payload = {
            "files": deploy_files,
            "draft": False
        }
        
        print(f"::notice::Creating deploy with {len(files_dict)} files...")
        response = requests.post(deploy_url, headers=headers, json=deploy_payload)
        
        if response.status_code == 200:
            deploy_data = response.json()
            deploy_id = deploy_data['id']
            print(f"::notice::Deploy created: {deploy_id}")
            
            # Step 2: Wait for deploy to be ready
            return wait_for_deploy_ready(site_id, auth_token, deploy_id)
        else:
            print(f"::error::Failed to create deploy: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"::error::Error creating deploy: {e}")
        traceback.print_exc()
        return None

def wait_for_deploy_ready(site_id, auth_token, deploy_id, max_wait=300):
    """Wait for deploy to be ready and return file URLs."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys/{deploy_id}"
    
    print(f"::notice::Waiting for deploy {deploy_id} to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(deploy_url, headers=headers)
        if response.status_code == 200:
            deploy_data = response.json()
            state = deploy_data.get('state', '')
            print(f"::notice::Deploy state: {state}")
            
            if state == 'ready':
                print(f"::notice::Deploy is ready!")
                # Get the deploy URL
                deploy_url_path = deploy_data.get('deploy_url', '')
                site_url = deploy_data.get('url', f'https://{site_id}.netlify.app')
                
                # Return the base URL for files
                return site_url
            elif state == 'error':
                print(f"::error::Deploy failed: {deploy_data}")
                return None
            
        time.sleep(10)  # Check every 10 seconds
    
    print(f"::error::Deploy timeout after {max_wait} seconds")
    return None

def upload_files_to_netlify(site_id, auth_token, file_paths):
    """Upload files to Netlify and wait for deployment."""
    try:
        # Create files dictionary for deploy
        files_dict = {}
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            files_dict[filename] = file_path
        
        # Create deploy and wait for completion
        site_url = create_deploy_with_files(site_id, auth_token, files_dict)
        
        if site_url:
            # Create file URLs
            file_urls = {}
            for filename in files_dict.keys():
                file_urls[filename] = f"{site_url}/{filename}"
            return file_urls
        else:
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
        uploaded_count = 0
        for filename, file_url in file_urls.items():
            urls[filename] = file_url
            
            # Delete local file after successful upload
            local_path = os.path.join(HTML_FOLDER, filename)
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"::notice::Deleted local file {filename}")
            
            uploaded_count += 1
        
        # Save updated URLs
        save_urls(urls)
        print(f"::notice::Successfully uploaded {uploaded_count} files to Netlify")
        
        # Verify uploads
        print(f"::notice::Verifying uploads...")
        for filename, file_url in file_urls.items():
            try:
                response = requests.head(file_url, timeout=10)
                if response.status_code == 200:
                    print(f"::notice::✓ {filename} is accessible at {file_url}")
                else:
                    print(f"::warning::✗ {filename} returned {response.status_code}")
            except Exception as e:
                print(f"::warning::Could not verify {filename}: {e}")
    else:
        print(f"::error::Failed to upload files to Netlify")
        print(f"::notice::Keeping local files for retry")

if __name__ == "__main__":
    main()

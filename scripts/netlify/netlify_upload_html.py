# scripts/netlify/netlify_upload_html.py
# scripts/netlify/netlify_upload_html.py
import os
import requests
import json
import traceback
import sys
import time
import hashlib
from typing import List, Dict, Optional

# --- Configuration ---
# Netlify API configuration
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

# Folder containing HTML files to upload and the file to store URLs
HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

# --- Utility Functions ---

def get_file_hash(file_path: str) -> str:
    """Calculates the SHA-1 hash of a file's content."""
    h = hashlib.sha1()
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def load_existing_urls() -> Dict[str, str]:
    """Load existing URLs from file."""
    if os.path.exists(URLS_FILE):
        try:
            with open(URLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"::warning::Could not decode existing {URLS_FILE}, starting fresh.")
            return {}
    return {}

def save_urls(urls_dict: Dict[str, str]):
    """Save URLs to file."""
    os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls_dict, f, indent=2, ensure_ascii=False)

def verify_upload(file_url: str) -> bool:
    """Verify that the uploaded file is accessible."""
    try:
        response = requests.head(file_url, timeout=10)
        if response.status_code == 200:
            print(f"::notice::✓ Verified: {file_url} is accessible")
            return True
        else:
            print(f"::warning::File not accessible: {file_url} - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"::warning::Could not verify {file_url}: {e}")
        return False

# --- Netlify API Functions ---

def create_initial_deploy(site_id: str, auth_token: str, file_manifest: Dict[str, str]) -> Optional[Dict]:
    """
    Initiates a new deploy by POSTing the file manifest.
    Netlify responds with the deploy ID and a list of 'required' file hashes.
    """
    deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    # The payload MUST include the `files` (manifest) to initiate the deploy process.
    payload = {
        "files": file_manifest,
        "title": f"QA Reports - {time.strftime('%Y-%m-%d %H:%M')}",
        "draft": True # IMPORTANT: Keeping this TRUE for a draft deploy to save credits
    }

    print("::notice::Initiating new deploy with file manifest...")
    response = requests.post(deploy_url, headers=headers, json=payload)

    if response.status_code == 200 or response.status_code == 201:
        deploy_data = response.json()
        print(f"::notice::Deploy initiated: ID {deploy_data['id']}")
        return deploy_data
    else:
        print(f"::error::Failed to initiate deploy: {response.status_code} - {response.text}")
        return None

def upload_missing_files(deploy_id: str, auth_token: str, required_hashes: List[str], file_paths: Dict[str, str]):
    """Uploads the file content for hashes required by the new deploy."""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/octet-stream"
    }
    
    uploaded_count = 0
    
    # We only upload files whose hash is in the 'required_hashes' list
    for file_path in file_paths.values():
        file_hash = get_file_hash(file_path)
        filename = os.path.basename(file_path)

        if file_hash in required_hashes:
            upload_url = f"{NETLIFY_API_BASE}/deploys/{deploy_id}/files/{file_hash}"
            
            with open(file_path, "rb") as f:
                file_content = f.read()

            print(f"::notice::Uploading missing file {filename} by hash {file_hash[:6]}...")
            response = requests.put(upload_url, headers=headers, data=file_content)

            if response.status_code == 200 or response.status_code == 201:
                uploaded_count += 1
            else:
                print(f"::error::Failed to upload file content for {filename}: {response.status_code} - {response.text}")
                # Crucial: If one file fails, the deploy will likely fail. We continue but this is a critical issue.
                
    print(f"::notice::Completed upload of {uploaded_count} required files.")


def wait_for_deploy_processing(site_id: str, auth_token: str, deploy_id: str, max_wait: int = 180) -> bool:
    """Wait for deploy to be processed and published."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    deploy_url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys/{deploy_id}"
    
    print(f"::notice::Waiting for deploy processing (max {max_wait}s)...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(deploy_url, headers=headers)
        if response.status_code == 200:
            deploy_data = response.json()
            state = deploy_data.get('state', '')
            print(f"::notice::Deploy state: {state}")
            
            if state == 'ready':
                print(f"::notice::Deploy processing complete and published!")
                return True
            elif state == 'error':
                print(f"::error::Deploy processing failed: {deploy_data.get('error_message', 'Unknown error')}")
                return False
        
        time.sleep(10)
    
    print(f"::warning::Deploy processing timeout after {max_wait}s.")
    return False

# --- Main Logic ---

def upload_files_to_netlify(site_id: str, auth_token: str, file_paths: List[str], site_name: str) -> Dict[str, str]:
    """
    Executes the complete Netlify deploy workflow for a list of files.
    Returns a dictionary of filename: url for successfully uploaded and verified files.
    """
    
    # 1. Create the File Manifest and Path Map
    file_manifest = {} # { '/filename.html': 'sha1_hash' }
    file_path_map = {} # { 'sha1_hash': '/path/to/local/file.html' }
    for full_path in file_paths:
        filename = os.path.basename(full_path)
        file_hash = get_file_hash(full_path)
        
        # The path in the manifest is the final path on the Netlify site.
        file_manifest[f"/{filename}"] = file_hash
        file_path_map[file_hash] = full_path

    # 2. Initiate Deploy with Manifest
    deploy_data = create_initial_deploy(site_id, auth_token, file_manifest)
    if not deploy_data:
        return {}
    
    deploy_id = deploy_data.get('id')
    required_hashes = deploy_data.get('required', [])
    
    # *** FIX: Retrieve the unique draft deploy URL for verification ***
    deploy_base_url = deploy_data.get('deploy_ssl_url')
    if not deploy_base_url:
        print("::error::Could not find deploy_ssl_url in deploy data. Cannot verify draft deploy.")
        return {}
    print(f"::notice::Draft Deploy URL Base: {deploy_base_url}")
    # ***************************************************************
    
    # 3. Upload Required Files
    if required_hashes:
        upload_missing_files(deploy_id, auth_token, required_hashes, {hash: path for hash, path in file_path_map.items()})
    else:
        print("::notice::No files required to upload (already on Netlify's CDN).")
        
    # 4. Wait for Deploy to Finalize
    deploy_success = wait_for_deploy_processing(site_id, auth_token, deploy_id)

    # 5. Final Verification and Cleanup
    successful_urls = {}
    # base_url = f"https://{site_name}.netlify.app" # OLD/INCORRECT for draft deploys
    
    if deploy_success:
        for full_path in file_paths:
            filename = os.path.basename(full_path)
            
            # *** FIX: Use the draft deploy's unique URL for verification ***
            file_url = f"{deploy_base_url}/{filename}"
            
            if verify_upload(file_url):
            # *************************************************************
                successful_urls[filename] = file_url
                
                # Delete local file after successful upload and verification
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"::notice::Deleted local file {filename}")
            else:
                print(f"::warning::Verification failed for {filename}, keeping local copy.")

    return successful_urls


def main():
    # --- Environment Check ---
    netlify_site_id = os.getenv("NETLIFY_SITE_ID")
    netlify_auth_token = os.getenv("NETLIFY_AUTH_TOKEN")
    netlify_site_name = os.getenv("NETLIFY_SITE_NAME") # Highly recommended to set this for URL creation
    
    if not netlify_site_id or not netlify_auth_token:
        print("::error::NETLIFY_SITE_ID or NETLIFY_AUTH_TOKEN not set")
        sys.exit(1)
        
    # Fallback/guess the site name if not explicitly set (no longer used for verification, but kept for clarity)
    if not netlify_site_name:
        print("::warning::NETLIFY_SITE_NAME not set. Using NETLIFY_SITE_ID for base URL construction (but draft URL is used for verification).")
        netlify_site_name = netlify_site_id

    # --- File Preparation ---
    if not os.path.exists(HTML_FOLDER):
        print(f"::notice::HTML folder '{HTML_FOLDER}' not found. Exiting.")
        return

    html_files = [f for f in os.listdir(HTML_FOLDER) if f.lower().endswith(".html")]
    if not html_files:
        print("::notice::No HTML files to upload to Netlify.")
        return

    # Prepare file paths
    file_paths = [os.path.join(HTML_FOLDER, f) for f in html_files]
    
    print(f"::notice::Starting upload process for {len(file_paths)} files to Netlify...")
    
    # --- Execute Upload ---
    uploaded_file_urls = upload_files_to_netlify(
        site_id=netlify_site_id, 
        auth_token=netlify_auth_token, 
        file_paths=file_paths,
        site_name=netlify_site_name # site_name is not strictly needed anymore, but keeping interface consistent
    )

    # --- Final Result Handling ---
    if uploaded_file_urls:
        # Load existing URLs to merge
        urls = load_existing_urls()
        urls.update(uploaded_file_urls)
        
        # Save updated URLs
        save_urls(urls)
        print(f"\n::notice::Successfully uploaded and verified {len(uploaded_file_urls)} files to Netlify")
        print(f"::notice::URLs saved are for the **temporary Draft Deploy URL** to avoid build costs.")
    else:
        print(f"\n::error::No files were successfully uploaded or verified on Netlify")
        print(f"::notice::Keeping local files for retry")

if __name__ == "__main__":
    main()

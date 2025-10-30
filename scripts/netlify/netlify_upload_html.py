# scripts/netlify/netlify_upload_html.py
import os
import json
import hashlib
import requests
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from netlify_encryptor import decrypt_file_to_bytes # Kept for the file check only

# --- Configuration ---
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

if not NETLIFY_SITE_ID or not NETLIFY_AUTH_TOKEN:
    print("::error::NETLIFY_SITE_ID or NETLIFY_AUTH_TOKEN not set.")
    sys.exit(1)

# Helper function to compute SHA-1 hash
def sha1_file(filepath):
    """Compute SHA-1 hash for a file."""
    hasher = hashlib.sha1()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def create_deploy_manifest():
    """Create a dictionary of {path: sha1} for all encrypted files."""
    manifest = {}
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.endswith(".html")]
    
    # Prefix files with a directory path if needed, but here we'll keep them flat
    for filename in html_files:
        local_path = os.path.join(HTML_FOLDER, filename)
        # Check if the file is valid (optional check, but good practice)
        if os.path.getsize(local_path) > 0:
            # Netlify path should be relative to the deploy root.
            # Assuming 'docs' is the publish directory, we use a subpath
            netlify_path = f"reports/{filename}"
            manifest[netlify_path] = sha1_file(local_path)
        else:
            print(f"::warning::Skipping empty file: {filename}")
            
    return manifest

def upload_to_netlify(manifest):
    """Initiate draft deploy, upload missing files, and get the deploy URL."""
    headers = {
        "Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Initiate Draft Deploy
    deploy_url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
    data = {"files": manifest, "draft": True} # <--- Ensure it is a DRAFT deploy
    print("::notice::Initiating Netlify draft deploy...")
    response = requests.post(deploy_url, headers=headers, json=data)
    response.raise_for_status()
    deploy_data = response.json()
    
    deploy_id = deploy_data.get("id")
    required_files = deploy_data.get("required", [])
    deploy_draft_url = deploy_data.get("deploy_ssl_url") # Use deploy_ssl_url or deploy_url
    
    print(f"::notice::Deploy ID: {deploy_id}. Files to upload: {len(required_files)}")

    # 2. Upload Required Files
    for file_sha in required_files:
        # Find the local path corresponding to the SHA
        local_path = next((os.path.join(HTML_FOLDER, os.path.basename(p))
                           for p, sha in manifest.items() if sha == file_sha), None)
        
        if local_path:
            upload_path = f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/{file_sha}"
            with open(local_path, "rb") as f:
                upload_response = requests.put(upload_path, headers=headers, data=f)
                upload_response.raise_for_status()
                print(f"::notice::Uploaded file with SHA: {file_sha}")
                
    # 3. Store Netlify URLs
    # Base URL is required for the dashboard links
    base_url = f"{deploy_draft_url.split('/deploy/')[0]}"
    
    urls = {}
    for netlify_path, sha in manifest.items():
        # The full URL for the report
        full_url = f"{base_url}/{netlify_path}"
        # The key for the URLS_FILE is just the filename
        filename = os.path.basename(netlify_path)
        urls[filename] = full_url

    # Save URLs to file for the next script (netlify_parse_html.py)
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)
        
    print(f"::notice::Successfully stored {len(urls)} URLs in {URLS_FILE}")
    print(f"::notice::Deploy finished. Draft URL: {base_url}")

def main():
    print("::notice::Starting Netlify upload process...")
    manifest = create_deploy_manifest()

    if not manifest:
        print("::notice::No encrypted HTML files found to upload.")
        return

    try:
        upload_to_netlify(manifest)
    except requests.exceptions.HTTPError as e:
        print(f"::error::Netlify HTTP Error: {e.response.status_code} - {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"::error::An unexpected error occurred during Netlify upload: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()

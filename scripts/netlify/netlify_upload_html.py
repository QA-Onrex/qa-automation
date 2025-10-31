# scripts/netlify/netlify_upload_html.py
import os
import json
import hashlib
import requests
import sys
# Make sure the path to netlify_encryptor.py is correct
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from netlify_encryptor import decrypt_file_to_bytes # Kept for the file check only

# --- Configuration ---
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"
HEADERS_FILENAME = "_headers" # New configuration variable

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
    """Create a dictionary of {path: sha1} for all encrypted files and the headers file."""
    manifest = {}
    
    # 1. Include all Encrypted HTML files
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.endswith(".html")]
    
    for filename in html_files:
        local_path = os.path.join(HTML_FOLDER, filename)
        if os.path.getsize(local_path) > 0:
            # Netlify path: "reports/filename"
            netlify_path = f"reports/{filename}"
            manifest[netlify_path] = sha1_file(local_path)
        else:
            print(f"::warning::Skipping empty file: {filename}")
            
    # 2. CRITICAL FIX: Include the _headers file in the manifest
    headers_local_path = os.path.join(HTML_FOLDER, HEADERS_FILENAME)
    
    if os.path.exists(headers_local_path):
        # Map to the root path (/_headers) so Netlify processes it as a configuration file
        netlify_headers_path = f"/{HEADERS_FILENAME}" 
        manifest[netlify_headers_path] = sha1_file(headers_local_path)
        print(f"::notice::Included deployment configuration file: {HEADERS_FILENAME}")
    else:
        print(f"::error::Missing required configuration file: {headers_local_path}. CORS will likely fail.")

    return manifest

def upload_to_netlify(manifest, report_file_count):
    """Initiate draft deploy, upload missing files, and get the deploy URL."""
    headers = {
        "Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Create deploy message
    deploy_message = f"Uploaded {report_file_count} report file(s)"
    if report_file_count == 0:
        deploy_message = "Configuration update only"
    
    # 1. Initiate Draft Deploy
    deploy_url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
    data = {
        "files": manifest, 
        "draft": True,
        "title": deploy_message  # Add deploy message
    }
    print(f"::notice::Initiating Netlify draft deploy: {deploy_message}")
    response = requests.post(deploy_url, headers=headers, json=data)
    response.raise_for_status()
    deploy_data = response.json()
    
    deploy_id = deploy_data.get("id")
    required_files = deploy_data.get("required", [])
    # IMPORTANT: The deploy_ssl_url gives us the specific draft URL (e.g., https://<hash>--<site>.netlify.app)
    deploy_draft_url = deploy_data.get("deploy_ssl_url") 
    
    print(f"::notice::Deploy ID: {deploy_id}. Files to upload: {len(required_files)}")

    # 2. Upload Required Files (Handles both HTML and _headers file)
    for file_sha in required_files:
        # We need to find the local path for the file based on its SHA
        local_path = None
        for netlify_path, sha in manifest.items():
            if sha == file_sha:
                # The local file is always inside HTML_FOLDER, and the file name is the last component
                filename = os.path.basename(netlify_path)
                # If it's the _headers file, use the actual filename
                if netlify_path == f"/{HEADERS_FILENAME}":
                     local_path = os.path.join(HTML_FOLDER, HEADERS_FILENAME)
                # Otherwise, it's an HTML file
                elif netlify_path.startswith("reports/"):
                    local_path = os.path.join(HTML_FOLDER, filename)
                break

        if local_path and os.path.exists(local_path):
            upload_path = f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/{file_sha}"
            with open(local_path, "rb") as f:
                upload_response = requests.put(upload_path, headers=headers, data=f)
                upload_response.raise_for_status()
                file_type = "headers" if netlify_path == f"/{HEADERS_FILENAME}" else "report"
                print(f"::notice::Uploaded {file_type} file with SHA: {file_sha}")
        else:
            print(f"::error::Failed to find local file for SHA: {file_sha}")
            
    # 3. Store Netlify URLs
    # Base URL is derived from the draft URL
    base_url = f"{deploy_draft_url.split('/deploy/')[0]}"
    
    urls = {}
    for netlify_path, sha in manifest.items():
        # Only process URLs for the report files, not the _headers file
        if netlify_path.startswith("reports/"):
            full_url = f"{base_url}/{netlify_path}"
            filename = os.path.basename(netlify_path)
            urls[filename] = full_url

    # Save URLs to file for the next script
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Successfully stored {len(urls)} URLs in {URLS_FILE}")
    print(f"::notice::Deploy finished. Draft URL: {base_url}")
    print(f"::notice::Deploy message: {deploy_message}")

def main():
    # Check if there are any report files to upload
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.endswith(".html") and f != HEADERS_FILENAME]
    report_file_count = len(html_files)
    
    if report_file_count == 0:
        print("::notice::No report files found in data/netlify_html. Skipping upload.")
        return
        
    manifest = create_deploy_manifest()

    if not manifest:
        print("::notice::No files found to upload.")
        return

    try:
        upload_to_netlify(manifest, report_file_count)
    except requests.exceptions.HTTPError as e:
        print(f"::error::Netlify HTTP Error: {e.response.status_code} - {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"::error::An unexpected error occurred during Netlify upload: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()

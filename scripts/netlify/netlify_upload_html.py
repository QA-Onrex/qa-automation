# scripts/netlify/netlify_upload_html.py
import os
import json
import hashlib
import requests
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from netlify_encryptor import decrypt_file_to_bytes

# Configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"
HEADERS_FILENAME = "_headers"

if not NETLIFY_SITE_ID or not NETLIFY_AUTH_TOKEN:
    print("❌ NETLIFY_SITE_ID or NETLIFY_AUTH_TOKEN not set")
    sys.exit(1)


def sha1_file(filepath):
    """Compute SHA-1 hash for file content"""
    hasher = hashlib.sha1()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()


def create_deploy_manifest():
    """Create deployment manifest with report files and headers configuration"""
    manifest = {}
    
    # Add all HTML report files to manifest
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.endswith(".html")]
    
    for filename in html_files:
        local_path = os.path.join(HTML_FOLDER, filename)
        if os.path.getsize(local_path) > 0:
            netlify_path = f"reports/{filename}"
            manifest[netlify_path] = sha1_file(local_path)
            print(f"Added to manifest: {filename}")
        else:
            print(f"Skipping empty file: {filename}")
            
    # Add _headers file for CORS configuration
    headers_local_path = os.path.join(HTML_FOLDER, HEADERS_FILENAME)
    
    if os.path.exists(headers_local_path):
        netlify_headers_path = f"/{HEADERS_FILENAME}"
        manifest[netlify_headers_path] = sha1_file(headers_local_path)
        print(f"Included configuration file: {HEADERS_FILENAME}")
    else:
        print(f"Missing configuration file: {headers_local_path}")

    return manifest


def upload_to_netlify(manifest, report_file_count):
    """Deploy files to Netlify and generate URLs for reports"""
    headers = {
        "Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Create deploy message based on file count
    deploy_message = f"Uploaded {report_file_count} report file(s)"
    if report_file_count == 0:
        deploy_message = "Configuration update only"
    
    # Initiate deploy with Netlify API
    print(f"Initiating Netlify deploy: {deploy_message}")
    deploy_url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
    data = {
        "files": manifest, 
        "draft": True,
        "title": deploy_message
    }
    
    response = requests.post(deploy_url, headers=headers, json=data)
    response.raise_for_status()
    deploy_data = response.json()
    
    deploy_id = deploy_data.get("id")
    required_files = deploy_data.get("required", [])
    deploy_draft_url = deploy_data.get("deploy_ssl_url")
    
    print(f"Deploy ID: {deploy_id}")
    print(f"Files to upload: {len(required_files)}")

    # Upload required files to Netlify
    for file_sha in required_files:
        local_path = None
        for netlify_path, sha in manifest.items():
            if sha == file_sha:
                filename = os.path.basename(netlify_path)
                if netlify_path == f"/{HEADERS_FILENAME}":
                    local_path = os.path.join(HTML_FOLDER, HEADERS_FILENAME)
                elif netlify_path.startswith("reports/"):
                    local_path = os.path.join(HTML_FOLDER, filename)
                break

        if local_path and os.path.exists(local_path):
            upload_path = f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/{file_sha}"
            with open(local_path, "rb") as f:
                upload_response = requests.put(upload_path, headers=headers, data=f)
                upload_response.raise_for_status()
            file_type = "headers" if netlify_path == f"/{HEADERS_FILENAME}" else "report"
            print(f"Uploaded {file_type} file: {os.path.basename(local_path)}")
        else:
            print(f"Failed to find local file for SHA: {file_sha}")
            
    # Generate and store report URLs
    base_url = f"{deploy_draft_url.split('/deploy/')[0]}"
    
    urls = {}
    for netlify_path, sha in manifest.items():
        if netlify_path.startswith("reports/"):
            full_url = f"{base_url}/{netlify_path}"
            filename = os.path.basename(netlify_path)
            urls[filename] = full_url

    # Save URLs for next processing step
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)
        
    print(f"Stored {len(urls)} URLs in {URLS_FILE}")
    print(f"Deploy finished: {base_url}")
    print(f"Deploy message: {deploy_message}")


def main():
    # Validate environment variables
    if not NETLIFY_SITE_ID or not NETLIFY_AUTH_TOKEN:
        print("❌ Missing Netlify credentials")
        sys.exit(1)

    try:
        # Check for report files to upload
        html_files = [f for f in os.listdir(HTML_FOLDER) if f.endswith(".html") and f != HEADERS_FILENAME]
        report_file_count = len(html_files)
        
        # Exit early if no report files found
        if report_file_count == 0:
            print("::notice::⏭️ Report files found: 0")
            return

        # Output annotation for found files
        print(f"::notice::📄 Report files found: {report_file_count}")

        # Create deployment manifest
        manifest = create_deploy_manifest()
        if not manifest:
            print("No files found in manifest")
            return

        # Upload to Netlify
        upload_to_netlify(manifest, report_file_count)
        
        # Output annotation for uploaded files
        print(f"::notice::✅ Report files uploaded: {report_file_count}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Netlify HTTP Error: {e.response.status_code} - {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

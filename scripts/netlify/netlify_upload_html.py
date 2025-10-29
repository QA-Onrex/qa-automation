# scripts/netlify/netlify_upload_html.py
import os
import requests
import json
import traceback
import sys
import base64
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Netlify API configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

def upload_file_direct(site_id, auth_token, file_path):
    """
    Upload file directly to Netlify using a simpler approach.
    This uses the form-based file upload which is more reliable.
    """
    try:
        filename = os.path.basename(file_path)
        
        # Read the encrypted file
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # Convert to base64 for reliable transmission
        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Netlify's form-based upload endpoint
        upload_url = f"https://api.netlify.com/api/v1/sites/{site_id}/files"
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": filename,
            "content": file_content_b64,
            "encoding": "base64"
        }
        
        print(f"::notice::Uploading {filename} via direct API...")
        response = requests.post(upload_url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            file_data = response.json()
            file_url = f"https://{site_id}.netlify.app/{filename}"
            print(f"::notice::Successfully uploaded {filename}")
            return file_url
        else:
            print(f"::error::Failed to upload {filename}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"::error::Error uploading {file_path}: {e}")
        traceback.print_exc()
        return None

def upload_files_simple(site_id, auth_token, file_paths):
    """
    Simple sequential upload of files.
    """
    file_urls = {}
    
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        file_url = upload_file_direct(site_id, auth_token, file_path)
        
        if file_url:
            file_urls[filename] = file_url
        else:
            print(f"::warning::Skipping {filename} due to upload failure")
    
    return file_urls

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
    file_urls = upload_files_simple(NETLIFY_SITE_ID, NETLIFY_AUTH_TOKEN, file_paths)
    
    if file_urls:
        # Update URLs and clean up
        uploaded_count = 0
        for filename, file_url in file_urls.items():
            # Verify the upload before deleting local file
            if verify_upload(file_url):
                urls[filename] = file_url
                
                # Delete local file after successful upload and verification
                local_path = os.path.join(HTML_FOLDER, filename)
                if os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"::notice::Deleted local file {filename}")
                
                uploaded_count += 1
            else:
                print(f"::warning::Upload verification failed for {filename}, keeping local copy")
        
        # Save updated URLs
        save_urls(urls)
        print(f"::notice::Successfully uploaded and verified {uploaded_count} files to Netlify")
    else:
        print(f"::error::No files were successfully uploaded to Netlify")
        print(f"::notice::Keeping local files for retry")

if __name__ == "__main__":
    main()

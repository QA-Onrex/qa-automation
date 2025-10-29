# scripts/netlify/netlify_upload_html.py
import os
import requests
import json
import traceback
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Netlify API configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"

def upload_file_to_netlify(file_path, site_id, auth_token):
    """Upload a file to Netlify and return the public URL."""
    try:
        # Read the encrypted file
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        filename = os.path.basename(file_path)
        
        # Netlify API endpoint for file uploads
        url = f"{NETLIFY_API_BASE}/sites/{site_id}/deploys"
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
        }
        
        # Prepare form data for file upload
        files = {
            'file': (filename, file_content, 'application/octet-stream')
        }
        
        data = {
            'name': filename
        }
        
        print(f"::notice::Uploading {filename} to Netlify...")
        response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            deploy_data = response.json()
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
        
        # Upload to Netlify
        file_url = upload_file_to_netlify(html_path, NETLIFY_SITE_ID, NETLIFY_AUTH_TOKEN)
        
        if file_url:
            # Store the URL mapping
            urls[html_file] = file_url
            uploaded_count += 1
            
            # Delete local HTML file after successful upload
            os.remove(html_path)
            print(f"::notice::Deleted local file {html_file} after successful Netlify upload")
        else:
            print(f"::warning::Failed to upload {html_file}, keeping local copy")

    # Save updated URLs
    save_urls(urls)
    print(f"::notice::Uploaded {uploaded_count} files to Netlify and updated URL mappings.")

if __name__ == "__main__":
    main()

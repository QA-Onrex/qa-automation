# scripts/netlify/netlify_upload_html.py
import os
import shutil
import json
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

HTML_FOLDER = "data/netlify_html"
NETLIFY_DEPLOY_FOLDER = "public"  # Netlify serves from /public by default
URLS_FILE = "data/netlify_urls.json"

def load_existing_urls():
    """Load existing URLs from file - ensure it returns a dict."""
    if os.path.exists(URLS_FILE):
        try:
            with open(URLS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # If it's a list, convert it to a dict
                if isinstance(data, list):
                    print("::warning::Converting URLs from list to dictionary format")
                    # Convert list of dicts to a single dict
                    new_dict = {}
                    for item in data:
                        if isinstance(item, dict):
                            # Take the first key-value pair from each dict
                            for key, value in item.items():
                                new_dict[key] = value
                                break
                    return new_dict
                return data
        except json.JSONDecodeError:
            print("::warning::URLs file is invalid, starting fresh")
            return {}
    return {}

def save_urls(urls_dict):
    """Save URLs to file as a dictionary."""
    os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
    with open(URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(urls_dict, f, indent=2, ensure_ascii=False)

def main():
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.lower().endswith(".html")]
    if not html_files:
        print("::notice::No HTML files to process.")
        return

    # Load existing URLs - this should now always return a dict
    urls = load_existing_urls()
    print(f"::notice::Loaded {len(urls)} existing URLs")
    
    # Ensure Netlify deploy folder exists
    os.makedirs(NETLIFY_DEPLOY_FOLDER, exist_ok=True)
    
    uploaded_count = 0

    for html_file in html_files:
        html_path = os.path.join(HTML_FOLDER, html_file)
        dest_path = os.path.join(NETLIFY_DEPLOY_FOLDER, html_file)
        
        # Copy file to Netlify deploy folder
        shutil.copy2(html_path, dest_path)
        
        # Create Netlify URL
        netlify_site_id = os.getenv('NETLIFY_SITE_ID', 'your-site')
        file_url = f"https://{netlify_site_id}.netlify.app/{html_file}"
        
        # This should now work - urls is a dict
        urls[html_file] = file_url
        uploaded_count += 1
        
        # Delete local HTML file after copy
        os.remove(html_path)
        print(f"::notice::Moved {html_file} to Netlify deploy folder")

    # Save updated URLs
    save_urls(urls)
    print(f"::notice::Processed {uploaded_count} files for Netlify deployment")
    print(f"::notice::Total URLs in mapping: {len(urls)}")

if __name__ == "__main__":
    main()

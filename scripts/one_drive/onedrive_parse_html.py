# scripts/one_drive/onedrive_parse_html.py
import os
import json
import re
import requests
import time
import hashlib
import base64
from datetime import datetime, timedelta
from urllib.parse import quote
from collections import defaultdict

# Import our encryptor
from onedrive_encryptor import encrypt_string

# OneDrive folder paths
ONEDRIVE_HTML_FOLDER = "qa-automation/data/html"
ONEDRIVE_PROCESSED_FOLDER = "qa-automation/data/reports"
ONEDRIVE_RESULTS_FILE = "qa-automation/data/results.json"

def get_onedrive_access_token():
    """Get access token using refresh token"""
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("ONEDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise Exception("OneDrive credentials missing")
    
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'https://graph.microsoft.com/Files.ReadWrite offline_access'
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get('access_token')
    else:
        raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

def download_from_onedrive_to_memory(file_path, access_token):
    """Download a file from OneDrive directly to memory"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/content"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Rate limiting
    time.sleep(0.5)
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    elif response.status_code == 404:
        print(f"ℹ️ File not found in OneDrive: {file_path}")
        return None
    else:
        print(f"❌ Failed to download {file_path}: {response.status_code}")
        return None

def upload_to_onedrive_from_memory(content, file_path, access_token):
    """Upload content to OneDrive file"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/content"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream'
    }
    
    # Rate limiting
    time.sleep(0.5)
    
    response = requests.put(url, headers=headers, data=content)
    if response.status_code in [200, 201]:
        print(f"✅ Uploaded {file_path} to OneDrive")
        return True
    else:
        print(f"❌ Failed to upload {file_path}: {response.status_code}")
        return False

def load_results_from_onedrive(access_token):
    """Load results.json from OneDrive"""
    print("📥 Loading results from OneDrive...")
    content = download_from_onedrive_to_memory(ONEDRIVE_RESULTS_FILE, access_token)
    
    if content:
        try:
            results = json.loads(content.decode('utf-8'))
            print(f"✅ Loaded {len(results)} records from OneDrive")
            return results
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse results.json from OneDrive: {e}")
            return []
    else:
        print("ℹ️ No existing results.json found in OneDrive, starting fresh")
        return []

def save_results_to_onedrive(results, access_token):
    """Save results.json to OneDrive with cleanup"""
    # Apply 8-week cleanup
    cleaned_results = cleanup_old_records(results, weeks=8)
    removed_count = len(results) - len(cleaned_results)
    
    if removed_count > 0:
        print(f"🧹 Cleaned up {removed_count} records older than 8 weeks")
        print(f"📊 Remaining records: {len(cleaned_results)}")
    
    # Convert to JSON
    content = json.dumps(cleaned_results, indent=2, ensure_ascii=False).encode('utf-8')
    
    # Upload to OneDrive
    if upload_to_onedrive_from_memory(content, ONEDRIVE_RESULTS_FILE, access_token):
        print(f"💾 Saved {len(cleaned_results)} records to OneDrive")
        return True
    else:
        print("❌ Failed to save results to OneDrive")
        return False

def create_onedrive_sharing_link(filename, access_token, expiry_days=90):
    """Create a long-term sharing link for a OneDrive file"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    file_path = f"qa-automation/data/reports/{filename}"
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/createLink"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Calculate expiry date
    expiry_date = datetime.now() + timedelta(days=expiry_days)
    
    link_data = {
        "type": "view",
        "scope": "anonymous",
        "expirationDateTime": expiry_date.isoformat() + "Z"
    }
    
    # Rate limiting
    time.sleep(0.5)
    
    response = requests.post(url, headers=headers, json=link_data)
    
    # Both 200 (OK) and 201 (Created) are success status codes
    if response.status_code in [200, 201]:
        sharing_info = response.json()
        web_url = sharing_info.get('link', {}).get('webUrl')
        if web_url:
            print(f"✅ Created {expiry_days}-day sharing link for {filename}")
            return web_url
        else:
            print(f"❌ Sharing link created but no webUrl found in response for {filename}")
    else:
        print(f"❌ Failed to create sharing link for {filename}: {response.status_code}")
        if response.status_code == 404:
            print(f"⚠️ File not found in OneDrive: {filename}")
        elif response.status_code == 403:
            print(f"⚠️ Permission denied for: {filename}")
    return None

def move_file_in_onedrive(source_path, destination_path, access_token):
    """Move a file within OneDrive"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_source_path = quote(source_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_source_path}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    move_data = {
        "parentReference": {
            "path": f"/drive/root:/{ONEDRIVE_PROCESSED_FOLDER}"
        },
        "name": os.path.basename(destination_path)
    }
    
    # Rate limiting
    time.sleep(0.5)
        
    response = requests.patch(url, headers=headers, json=move_data)
    return response.status_code in [200, 201]

def list_onedrive_files(folder_path, access_token):
    """List files in a OneDrive folder"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(folder_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/children"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        items = response.json().get('value', [])
        return [item['name'] for item in items if 'file' in item]
    else:
        print(f"❌ Failed to list files in {folder_path}: {response.status_code}")
        return []

def compute_retry_count(test_suite_id, start_time, results, hours=10):
    """Compute retry count using chronological results, stop when older than 10 hours."""
    retry_count = 0
    if not test_suite_id or not start_time:
        return 0
    try:
        start_dt = datetime.strptime(start_time.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")
        time_threshold = start_dt - timedelta(hours=hours)

        # Iterate results in reverse chronological order
        for rec in reversed(results):
            rec_start = rec.get("start")
            if not rec_start:
                continue
            rec_dt = datetime.strptime(rec_start.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")

            # Stop as soon as the record is older than 10 hours
            if rec_dt < time_threshold:
                break

            if rec.get("test_suite_id") == test_suite_id:
                retry_count += 1

    except Exception:
        pass

    return retry_count

def parse_html_content(html_content, html_filename):
    """Parse embedded JSON from HTML content and extract all test data fields with color coding."""
    try:
        content = html_content.decode("utf-8")

        # Extract JSON inside loadExecutionData('main', {...})
        match = re.search(r"loadExecutionData\('main',\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"::warning::No embedded JSON found in {html_filename}")
            return None

        data_json = json.loads(match.group(1))
        entity = data_json.get("entity", {})

        # Project is outside entity
        project_name = data_json.get("project", {}).get("name")

        test_suite_id = entity.get("entityId")
        profile = entity.get("context", {}).get("profile")

        stats = entity.get("statistics", {})
        test_cases = stats.get("total")
        passed = stats.get("passed")
        failed = stats.get("failed")
        error = stats.get("errored")
        incomplete = stats.get("incomplete")
        skipped = stats.get("skipped")

        start = entity.get("startTime")
        end = entity.get("endTime")

        # Compute duration in minutes
        duration = None
        if start and end:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in start or '-' in start else "%Y-%m-%dT%H:%M:%S.%fZ"
                start_dt = datetime.strptime(start.replace('Z', '+0000'), fmt)
                end_dt = datetime.strptime(end.replace('Z', '+0000'), fmt)
                duration = (end_dt - start_dt).total_seconds() / 60  # minutes
            except Exception:
                duration = None

        # Compute retry count dynamically
        # Note: We'll compute this during dashboard build since we don't have all results here
        retry_count = 0

        # Sum check
        sum_check = True
        if test_cases is not None:
            total_sum = sum(filter(None, [passed, failed, error, incomplete, skipped]))
            sum_check = (total_sum == test_cases)

        # Color logic (basic - will be finalized in dashboard)
        color = "Red"  # default
        if test_cases is not None and passed == test_cases and sum_check:
            color = "Green"
            if retry_count and retry_count != 0:
                color = "Yellow"

        return {
            "html_file": f"qa-automation/data/reports/{html_filename}",  # Original OneDrive path
            "project": project_name,
            "test_suite_id": test_suite_id,
            "profile": profile,
            "test_cases": test_cases,
            "passed": passed,
            "failed": failed,
            "error": error,
            "incomplete": incomplete,
            "skipped": skipped,
            "start": start,
            "end": end,
            "duration": duration,
            "retry_count": retry_count,  # Will be computed in dashboard
            "sum_check": sum_check,
            "color": color  # Will be finalized in dashboard
        }

    except Exception as e:
        print(f"::error::Failed to parse {html_filename}: {e}")
        return None

def main():
    print("🔄 Processing HTML files from OneDrive...")
    
    # Get password from environment for encryption
    password = os.getenv("REPORT_PASSWORD", "")
    if not password:
        print("::warning::REPORT_PASSWORD not set. Encrypted URLs will not be generated.")
    
    try:
        # Get OneDrive access token
        access_token = get_onedrive_access_token()
                
        # Load existing results from OneDrive
        results = load_results_from_onedrive(access_token)
        
        # List HTML files in OneDrive
        html_files = [f for f in list_onedrive_files(ONEDRIVE_HTML_FOLDER, access_token) 
                     if f.lower().endswith(".html")]
        
        if not html_files:
            print("::notice::Processed 0 HTML files")
            return

        processed_count = 0
        new_results = []
        encrypted_links_created = 0
        encrypted_links_failed = 0
        
        for html_file in html_files:
            try:
                print(f"🔍 Processing {html_file}...")
                
                # Download HTML from OneDrive directly to memory
                html_path = f"{ONEDRIVE_HTML_FOLDER}/{html_file}"
                html_content = download_from_onedrive_to_memory(html_path, access_token)
                
                if not html_content:
                    continue
                
                # Parse HTML content
                data = parse_html_content(html_content, html_file)
                if not data:
                    print(f"::warning::Skipping {html_file} due to parsing error.")
                    continue
                
                # FIRST: Move HTML to processed folder in OneDrive
                destination_path = f"{ONEDRIVE_PROCESSED_FOLDER}/{html_file}"
                if move_file_in_onedrive(html_path, destination_path, access_token):
                    print(f"✅ Moved {html_file} to reports folder")
                    
                    # Wait for OneDrive to process the move operation
                    print("⏳ Waiting for OneDrive to process file move...")
                    time.sleep(3)  # 3 second delay for OneDrive sync
                    
                    # SECOND: Create and encrypt sharing link AFTER file is moved and synced
                    if password:
                        sharing_link = create_onedrive_sharing_link(html_file, access_token, expiry_days=90)
                        if sharing_link:
                            try:
                                encrypted_url = encrypt_string(sharing_link, password)
                                data["encrypted_url"] = encrypted_url
                                encrypted_links_created += 1
                                print(f"🔐 Encrypted link created for {html_file}")
                            except Exception as e:
                                print(f"❌ Failed to encrypt link for {html_file}: {e}")
                                encrypted_links_failed += 1
                                data["encrypted_url"] = None
                        else:
                            print(f"⚠️ Failed to create sharing link for {html_file}")
                            encrypted_links_failed += 1
                            data["encrypted_url"] = None
                    else:
                        data["encrypted_url"] = None
                    
                    new_results.append(data)
                    processed_count += 1
                    print(f"✅ Successfully processed {html_file}")
                else:
                    print(f"❌ Failed to move {html_file} to reports folder")
                    # Still add to results but without encrypted URL
                    data["encrypted_url"] = None
                    new_results.append(data)
                    processed_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing {html_file}: {e}")

        print(f"📊 Encrypted links: {encrypted_links_created} created, {encrypted_links_failed} failed")

        # Add new results to existing results and save to OneDrive
        if new_results:
            results.extend(new_results)
            print(f"📊 Added {len(new_results)} new records to results")
            
            # Save updated results to OneDrive
            if save_results_to_onedrive(results, access_token):
                print(f"💾 Successfully updated OneDrive with {len(results)} total records")
            else:
                print("❌ Failed to update results in OneDrive")
        else:
            print("ℹ️ No new results to save")

        # Final annotation with processed count
        print(f"::notice::Parsed {processed_count} HTML files with {encrypted_links_created} encrypted links")
        print(f"🎉 Processed {processed_count} out of {len(html_files)} HTML files")

    except Exception as e:
        print(f"❌ OneDrive processing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

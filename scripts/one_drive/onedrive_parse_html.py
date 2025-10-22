# scripts/one_drive/onedrive_parse_html.py
import os
import json
import re
import requests
import time
from datetime import datetime, timedelta
from urllib.parse import quote

# OneDrive folder paths
ONEDRIVE_HTML_FOLDER = "qa-automation/data/html"
ONEDRIVE_PROCESSED_FOLDER = "qa-automation/data/reports"
RESULTS_FILE = "data/results.json"

# Load existing results.json into memory
results = []
if os.path.exists(RESULTS_FILE):
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print("::warning::results.json is empty or invalid, starting fresh.")
        results = []

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
    else:
        print(f"❌ Failed to download {file_path}: {response.status_code}")
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

def ensure_onedrive_folder(folder_path, access_token):
    """Ensure a folder exists in OneDrive"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    
    # Check if folder exists
    safe_path = quote(folder_path)
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        # Folder doesn't exist, create it
        parent_path = '/'.join(folder_path.split('/')[:-1])
        folder_name = folder_path.split('/')[-1]
        
        create_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{parent_path}:/children"
        folder_data = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        
        create_response = requests.post(create_url, headers=headers, json=folder_data)
        if create_response.status_code in [200, 201]:
            print(f"📁 Created folder: {folder_path}")
        else:
            print(f"⚠️ Could not create folder {folder_path}")

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
        retry_count = compute_retry_count(test_suite_id, start, results)

        # Sum check
        sum_check = True
        if test_cases is not None:
            total_sum = sum(filter(None, [passed, failed, error, incomplete, skipped]))
            sum_check = (total_sum == test_cases)

        # Color logic
        color = "Red"  # default
        if test_cases is not None and passed == test_cases and sum_check:
            color = "Green"
            if retry_count and retry_count != 0:
                color = "Yellow"

        return {
            "html_file": f"qa-automation/data/reports/{html_filename}",  # Fixed path to match OneDrive
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
            "retry_count": retry_count,
            "sum_check": sum_check,
            "color": color
        }

    except Exception as e:
        print(f"::error::Failed to parse {html_filename}: {e}")
        return None

def main():
    print("🔄 Processing HTML files from OneDrive...")
    
    try:
        # Get OneDrive access token
        access_token = get_onedrive_access_token()
        
        # Ensure processed folder exists
        ensure_onedrive_folder(ONEDRIVE_PROCESSED_FOLDER, access_token)
        
        # List HTML files in OneDrive
        html_files = [f for f in list_onedrive_files(ONEDRIVE_HTML_FOLDER, access_token) 
                     if f.lower().endswith(".html")]
        
        if not html_files:
            print("::notice::Processed 0 HTML files")
            return

        processed_count = 0
        new_results = []
        
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
                if data:
                    new_results.append(data)
                    processed_count += 1
                    
                    # Move HTML to processed folder in OneDrive
                    destination_path = f"{ONEDRIVE_PROCESSED_FOLDER}/{html_file}"
                    if move_file_in_onedrive(html_path, destination_path, access_token):
                        print(f"✅ Processed and moved {html_file} to reports folder")
                    else:
                        print(f"⚠️ Processed {html_file} but failed to move to reports folder")
                else:
                    print(f"::warning::Skipping {html_file} due to parsing error.")
                    
            except Exception as e:
                print(f"❌ Error processing {html_file}: {e}")

        # Add new results to existing results
        if new_results:
            results.extend(new_results)
            print(f"📊 Added {len(new_results)} new records to results")
            
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
            
            # Save results.json locally
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved {len(results)} total records to {RESULTS_FILE}")
            
            # Verify the file was written
            if os.path.exists(RESULTS_FILE):
                file_size = os.path.getsize(RESULTS_FILE)
                print(f"📄 Results file verified: {file_size} bytes")
            else:
                print("❌ ERROR: results.json was not created!")
        else:
            print("ℹ️ No new results to save")

        # Final annotation with processed count
        print(f"::notice::Parsed {processed_count} HTML files")
        print(f"🎉 Processed {processed_count} out of {len(html_files)} HTML files")

    except Exception as e:
        print(f"❌ OneDrive processing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

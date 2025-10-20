# scripts/one_drive/onedrive_fetch_emails.py
import imaplib
import email
import os
import traceback
import requests
from datetime import datetime

# --- Config ---
zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")

IMAP_SERVER = "imap.zoho.eu"
SOURCE_FOLDER = "Automation"
PROCESSED_FOLDER = "Automation/Processed"

# OneDrive configuration
ONEDRIVE_FOLDER = "qa-automation/data/attachments"

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
        # Log if we got a new refresh token (for debugging)
        new_refresh_token = tokens.get('refresh_token')
        if new_refresh_token and new_refresh_token != refresh_token:
            print("::notice::New refresh token available - will be updated by token job")
        
        return tokens.get('access_token')
    else:
        raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

def upload_to_onedrive(file_content, filename, access_token):
    """Upload file to OneDrive"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_filename = requests.utils.quote(filename)
    
    # Upload to qa-automation/attachments folder
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{ONEDRIVE_FOLDER}/{safe_filename}:/content"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/octet-stream'
    }
    
    response = requests.put(url, headers=headers, data=file_content)
    
    if response.status_code in [200, 201]:
        print(f"✅ Uploaded {filename} to OneDrive")
        return True
    else:
        print(f"❌ Failed to upload {filename}: {response.status_code}")
        return False

def create_onedrive_folder(access_token):
    """Ensure the target folder exists in OneDrive"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    
    # Create the folder structure
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{ONEDRIVE_FOLDER}"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Check if folder exists
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        # Folder doesn't exist, create it
        parent_path = '/'.join(ONEDRIVE_FOLDER.split('/')[:-1])
        folder_name = ONEDRIVE_FOLDER.split('/')[-1]
        
        create_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{parent_path}:/children"
        folder_data = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        
        create_response = requests.post(create_url, headers=headers, json=folder_data)
        if create_response.status_code in [200, 201]:
            print(f"📁 Created folder: {ONEDRIVE_FOLDER}")
        else:
            print(f"⚠️ Could not create folder: {create_response.text}")

def save_attachments_to_onedrive(msg, access_token):
    """Save all ZIP attachments from email to OneDrive"""
    saved_files = []
    for part in msg.walk():
        content_disposition = part.get("Content-Disposition", "")
        filename = part.get_filename()

        if filename and filename.lower().endswith(".zip") and "attachment" in content_disposition:
            try:
                content_bytes = part.get_payload(decode=True)
                if not content_bytes:
                    print(f"⚠️ Empty ZIP attachment {filename}")
                    continue

                # Upload directly to OneDrive
                if upload_to_onedrive(content_bytes, filename, access_token):
                    saved_files.append(filename)

            except Exception as e:
                print(f"❌ Failed to upload {filename}: {e}")
                traceback.print_exc()

    return saved_files

def move_message(mail, msg_uid):
    """Move email to processed folder"""
    try:
        resp = mail.uid("MOVE", msg_uid, PROCESSED_FOLDER)
        if resp[0] == "OK":
            print(f"✅ Moved email UID {msg_uid.decode()}")
            return True
        else:
            # Fallback: copy and mark as deleted
            copy_resp = mail.uid("COPY", msg_uid, PROCESSED_FOLDER)
            if copy_resp[0] != "OK":
                print(f"⚠️ Failed to copy UID {msg_uid.decode()}")
                return False
            mail.uid("STORE", msg_uid, "+FLAGS", "(\Deleted)")
            return True
    except Exception as e:
        print(f"❌ Error moving message: {e}")
        return False

def main():
    print("🚀 Starting OneDrive Email Fetch...")
    print(f"📧 Source: {zoho_user}")
    print(f"📁 Destination: OneDrive/{ONEDRIVE_FOLDER}")
    
    # Get OneDrive access token
    try:
        access_token = get_onedrive_access_token()
        create_onedrive_folder(access_token)
    except Exception as e:
        print(f"❌ OneDrive authentication failed: {e}")
        return

    # Connect to email
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(zoho_user, zoho_pass)
    except Exception as e:
        print(f"❌ Email login failed: {e}")
        return

    try:
        status, _ = mail.select(SOURCE_FOLDER)
        if status != "OK":
            print(f"❌ Failed to select folder: {SOURCE_FOLDER}")
            return

        status, data = mail.uid("search", None, "ALL")
        if status != "OK":
            print("❌ Failed to search emails.")
            return

        uids = data[0].split()
        print(f"📧 Found {len(uids)} emails in '{SOURCE_FOLDER}'")

        processed_count = 0
        for uid in uids:
            try:
                typ, msg_data = mail.uid("fetch", uid, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                if not raw_email:
                    continue

                msg = email.message_from_bytes(raw_email)
                subject = msg.get("subject", "(no subject)")
                print(f"📨 Processing: {subject[:50]}...")

                saved_files = save_attachments_to_onedrive(msg, access_token)
                if saved_files and move_message(mail, uid):
                    processed_count += 1

            except Exception as e:
                print(f"❌ Error processing email UID {uid.decode()}: {e}")

        print(f"✅ Processed {processed_count} emails with attachments")

    finally:
        mail.expunge()
        mail.logout()

if __name__ == "__main__":
    main()

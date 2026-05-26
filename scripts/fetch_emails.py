# scripts/fetch_emails.py
import imaplib
import email
import os
import traceback
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from encryptor import encrypt_bytes_to_file

# Configuration
zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")
encrypt_password = os.getenv("REPORT_PASSWORD")

IMAP_SERVER = "imap.zoho.eu"
SOURCE_FOLDER = "Automation"
PROCESSED_FOLDER = "Automation/Processed"
ATTACHMENTS_FOLDER = "data/netlify_attachments"

os.makedirs(ATTACHMENTS_FOLDER, exist_ok=True)


def move_message(mail, msg_uid):
    """Move email to processed folder using MOVE command with COPY fallback"""
    try:
        # First try MOVE command
        resp = mail.uid("MOVE", msg_uid, PROCESSED_FOLDER)
        if resp[0] == "OK":
            print(f"Moved email UID {msg_uid.decode()} via MOVE")
            return True
        else:
            # Fallback to COPY + DELETE
            copy_resp = mail.uid("COPY", msg_uid, PROCESSED_FOLDER)
            if copy_resp[0] != "OK":
                print(f"Failed to copy UID {msg_uid.decode()} - skipping delete")
                return False
            mail.uid("STORE", msg_uid, "+FLAGS", "(\\Deleted)")
            print(f"Copied and marked for deletion UID {msg_uid.decode()}")
            return True
    except Exception as e:
        print(f"Error moving message UID {msg_uid.decode()}: {e}")
        traceback.print_exc()
        return False


def save_attachments(msg):
    """Extract and encrypt ZIP attachments from email message"""
    if not encrypt_password:
        print("REPORT_PASSWORD not set - cannot encrypt attachments")
        return []

    saved_files = []
    for part in msg.walk():
        content_disposition = part.get("Content-Disposition", "")
        filename = part.get_filename()

        # Process only ZIP attachments
        if filename and filename.lower().endswith(".zip") and "attachment" in content_disposition:
            try:
                content_bytes = part.get_payload(decode=True)
                if not content_bytes:
                    print(f"Empty ZIP attachment {filename}")
                    continue

                encrypted_path = os.path.join(ATTACHMENTS_FOLDER, filename)
                
                # Encrypt attachment directly from memory
                encrypt_bytes_to_file(content_bytes, encrypted_path)
                saved_files.append(filename)
                print(f"Encrypted and saved attachment: {filename}")

            except Exception as e:
                print(f"Failed to encrypt attachment {filename}: {e}")
                traceback.print_exc()

    return saved_files


def fetch_email_safely(mail, uid):
    """Safely fetch email with retry logic and proper error handling"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Add a small delay before fetching
            if attempt > 0:
                time.sleep(retry_delay)
                # Re-select the folder to reset connection state
                mail.select(SOURCE_FOLDER)
            
            # Fetch email content
            typ, msg_data = mail.uid("fetch", uid, "(RFC822)")
            
            if typ != "OK" or not msg_data or not msg_data[0]:
                print(f"Failed to fetch email UID {uid.decode()}, attempt {attempt + 1}")
                continue
                
            raw_email = msg_data[0][1]
            if not raw_email:
                print(f"Empty email UID {uid.decode()}, attempt {attempt + 1}")
                continue
                
            return raw_email
            
        except imaplib.IMAP4.abort as e:
            print(f"IMAP abort error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise
            # Reconnect on abort error
            return None, True  # Signal to reconnect
        except Exception as e:
            print(f"Unexpected error fetching email (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                raise
                
    return None


def reconnect_imap():
    """Reconnect to IMAP server"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(zoho_user, zoho_pass)
        mail.select(SOURCE_FOLDER)
        print("Reconnected to IMAP server")
        return mail
    except Exception as e:
        print(f"Failed to reconnect: {e}")
        raise


def main():
    # Validate required environment variables
    if not all([zoho_user, zoho_pass, encrypt_password]):
        print("❌ Missing required environment variables")
        sys.exit(1)

    mail = None
    try:
        # Connect to IMAP server
        print("Connecting to Zoho IMAP server...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(zoho_user, zoho_pass)
        print(f"Connected as {zoho_user}")

        # Select source folder
        status, _ = mail.select(SOURCE_FOLDER)
        if status != "OK":
            print(f"Failed to select folder: {SOURCE_FOLDER}")
            sys.exit(1)

        # Search for all emails
        status, data = mail.uid("search", None, "ALL")
        if status != "OK":
            print("Failed to search emails")
            sys.exit(1)

        uids = data[0].split()
                
        # Exit early if no emails found
        if len(uids) == 0:
            print("::notice::⏭️ Emails found: 0")
            mail.logout()
            return

        # Output annotation for found emails
        print(f"::notice::📧 Emails found: {len(uids)}")
        
        processed_count = 0
        need_reconnect = False
        
        # Process each email
        for uid in uids:
            if need_reconnect:
                try:
                    mail.logout()
                except:
                    pass
                mail = reconnect_imap()
                need_reconnect = False
            
            uid_str = uid.decode()
            try:
                # Fetch email content safely
                raw_email = fetch_email_safely(mail, uid)
                
                if raw_email is None:
                    print(f"Skipping email UID {uid_str} after retries")
                    continue

                # Parse email and extract subject
                msg = email.message_from_bytes(raw_email)
                subject = msg.get("subject", "(no subject)")
                print(f"Processing email: {subject[:100]}...")  # Truncate long subjects

                # Save and encrypt attachments
                saved_files = save_attachments(msg)
                if not saved_files:
                    print(f"No ZIP attachments found for UID {uid_str}")
                    continue

                # Move email to processed folder
                if move_message(mail, uid):
                    processed_count += 1
                    print(f"Successfully processed email: {subject[:100]}")

            except imaplib.IMAP4.abort as e:
                print(f"IMAP abort error processing UID {uid_str}: {e}")
                need_reconnect = True
                continue
            except Exception as e:
                print(f"Error processing email UID {uid_str}: {e}")
                traceback.print_exc()

        # Try to expunge if connection is still alive
        if mail and not need_reconnect:
            try:
                mail.expunge()
            except Exception as e:
                print(f"Error during expunge: {e}")
        
        if mail:
            try:
                mail.logout()
            except:
                pass
        
        # Output annotation for processed emails
        print(f"::notice::✅ Emails processed: {processed_count}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

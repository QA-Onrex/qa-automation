import imaplib
import email
import os
import traceback
import zipfile
import json
from bs4 import BeautifulSoup

# --- Configuration ---
zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")

IMAP_SERVER = "imap.zoho.eu"
SOURCE_FOLDER = "Automation"
PROCESSED_FOLDER = "Automation/Processed"

DATA_FOLDER = "data"
HTML_FOLDER = os.path.join(DATA_FOLDER, "html")
RESULTS_FILE = os.path.join(DATA_FOLDER, "results.json")

# Ensure html folder exists
os.makedirs(HTML_FOLDER, exist_ok=True)

# Load existing results.json if exists
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)
else:
    results = []

def move_message(mail, msg_uid):
    """Safely move a message to another folder."""
    try:
        resp = mail.uid("MOVE", msg_uid, PROCESSED_FOLDER)
        if resp[0] == "OK":
            print(f"::notice::Moved email UID {msg_uid.decode()} successfully via MOVE.")
            return True
        else:
            # fallback copy + delete
            copy_resp = mail.uid("COPY", msg_uid, PROCESSED_FOLDER)
            if copy_resp[0] != "OK":
                print(f"::error::Failed to copy UID {msg_uid.decode()}. Skipping delete.")
                return False
            mail.uid("STORE", msg_uid, "+FLAGS", "(\Deleted)")
            return True
    except Exception as e:
        print(f"::error::Error moving message UID {msg_uid.decode()}: {e}")
        traceback.print_exc()
        return False

def extract_html_from_zip(zip_bytes, html_filename):
    """Extracts the first HTML file from the ZIP bytes and saves it."""
    try:
        with zipfile.ZipFile(zip_bytes) as z:
            # Find the HTML file
            html_files = [f for f in z.namelist() if f.lower().endswith(".html")]
            if not html_files:
                print("::warning::No HTML file found in ZIP.")
                return None
            html_file_name_in_zip = html_files[0]
            # Extract and save
            extracted_path = os.path.join(HTML_FOLDER, html_filename)
            with z.open(html_file_name_in_zip) as html_file, open(extracted_path, "wb") as out_file:
                out_file.write(html_file.read())
            return extracted_path
    except Exception as e:
        print(f"::error::Failed to extract HTML from ZIP: {e}")
        traceback.print_exc()
        return None

def parse_project_field(html_path):
    """Parse the Project field from HTML using BeautifulSoup."""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        # Use the span class from your example
        project_span = soup.find("span", class_="styled-pu1pnnpa css-ur07o6me")
        if project_span:
            return project_span.text.strip()
        else:
            print("::warning::Project field not found in HTML.")
            return None
    except Exception as e:
        print(f"::error::Failed to parse HTML {html_path}: {e}")
        traceback.print_exc()
        return None

def main():
    print(f"Connecting to Zoho IMAP as {zoho_user}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(zoho_user, zoho_pass)

    status, _ = mail.select(SOURCE_FOLDER)
    if status != "OK":
        print(f"::error::Failed to select folder: {SOURCE_FOLDER}")
        return

    status, data = mail.uid("search", None, "ALL")
    if status != "OK":
        print("::error::Failed to search emails.")
        return

    uids = data[0].split()
    print(f"::notice::Found {len(uids)} emails in '{SOURCE_FOLDER}'.")

    processed_count = 0

    for uid in uids:
        try:
            typ, msg_data = mail.uid("fetch", uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                print(f"::warning::Failed to fetch email UID {uid.decode()}")
                continue

            raw_email = msg_data[0][1]
            if not raw_email:
                print(f"::warning::Empty email data for UID {uid.decode()}")
                continue

            msg = email.message_from_bytes(raw_email)
            subject = msg.get("subject", "(no subject)")
            print(f"::notice::Processing email: {subject}")

            # --- Process ZIP attachment ---
            zip_payload = None
            zip_name = None
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                if "attachment" in content_disposition and part.get_filename().lower().endswith(".zip"):
                    zip_payload = part.get_payload(decode=True)
                    zip_name = part.get_filename()
                    break

            if not zip_payload:
                print(f"::warning::No ZIP attachment found for email UID {uid.decode()}")
                continue

            html_filename = os.path.splitext(zip_name)[0] + ".html"
            html_path = extract_html_from_zip(zip_payload, html_filename)
            if not html_path:
                continue

            project = parse_project_field(html_path)

            # Append to results.json (for now only Project field)
            results.append({
                "email_subject": subject,
                "html_file": f"data/html/{html_filename}",
                "project": project
            })

            # Move email safely
            if move_message(mail, uid):
                processed_count += 1

        except Exception as e:
            print(f"::error::Error processing email UID {uid.decode()}: {e}")
            traceback.print_exc()

    # Save results.json
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    mail.expunge()  # delete only if safely moved
    mail.logout()
    print(f"::notice::Processed {processed_count} emails and updated results.json.")


if __name__ == "__main__":
    main()

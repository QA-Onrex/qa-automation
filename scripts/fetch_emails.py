import imaplib
import email
import os
import traceback

# Credentials from GitHub Secrets
zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")

IMAP_SERVER = "imap.zoho.com"
SOURCE_FOLDER = "Automation"
PROCESSED_FOLDER = "Automation/Processed"

def main():
    print(f"Connecting to Zoho IMAP as {zoho_user}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(zoho_user, zoho_pass)

    # Select source folder
    status, _ = mail.select(SOURCE_FOLDER)
    if status != "OK":
        print(f"::error::Failed to select folder: {SOURCE_FOLDER}")
        return

    # Fetch all emails
    status, data = mail.search(None, "ALL")
    if status != "OK":
        print("::error::Failed to search emails.")
        return

    mail_ids = data[0].split()
    print(f"::notice::Found {len(mail_ids)} emails in '{SOURCE_FOLDER}'.")

    processed_count = 0

    for num in mail_ids:
        try:
            # Fetch email data (headers only for now)
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                print(f"::warning::Failed to fetch email {num}")
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = msg["subject"]
            print(f"::notice::Processing email: {subject}")

            # TODO: later – extract ZIP, parse HTML, update results.json

            # Move to processed folder
            mail.copy(num, PROCESSED_FOLDER)
            mail.store(num, "+FLAGS", "\\Deleted")  # mark for deletion
            processed_count += 1

        except Exception as e:
            print(f"::error::Error processing email {num}: {e}")
            traceback.print_exc()

    # Delete moved messages
    mail.expunge()
    mail.logout()

    print(f"::notice::Processed {processed_count} emails and moved them to '{PROCESSED_FOLDER}'.")


if __name__ == "__main__":
    main()

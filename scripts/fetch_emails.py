import imaplib
import email
import os
import traceback

# --- Configuration ---
zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")

IMAP_SERVER = "imap.zoho.eu"
SOURCE_FOLDER = "Automation"
PROCESSED_FOLDER = "Automation/Processed"


def move_message(mail, msg_uid):
    """Safely move a message to another folder."""
    try:
        # Try MOVE first (supported by Zoho)
        resp = mail.uid("MOVE", msg_uid, PROCESSED_FOLDER)
        if resp[0] == "OK":
            print(f"::notice::Moved email UID {msg_uid.decode()} successfully via MOVE.")
            return True
        else:
            print(f"::warning::MOVE failed for {msg_uid.decode()}, trying COPY+DELETE...")

            # Fallback: COPY then DELETE
            copy_resp = mail.uid("COPY", msg_uid, PROCESSED_FOLDER)
            if copy_resp[0] != "OK":
                print(f"::error::Failed to copy UID {msg_uid.decode()} to {PROCESSED_FOLDER}. Skipping delete.")
                return False

            mail.uid("STORE", msg_uid, "+FLAGS", "(\Deleted)")
            print(f"::notice::Copied and marked for deletion UID {msg_uid.decode()}.")
            return True

    except Exception as e:
        print(f"::error::Error moving message UID {msg_uid.decode()}: {e}")
        traceback.print_exc()
        return False


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

            # TODO: parse ZIP & HTML next

            if move_message(mail, uid):
                processed_count += 1

        except Exception as e:
            print(f"::error::Error processing email UID {uid.decode()}: {e}")
            traceback.print_exc()

    mail.expunge()  # clean up deleted only if marked after successful copy
    mail.logout()
    print(f"::notice::Processed {processed_count} emails and safely moved them to '{PROCESSED_FOLDER}'.")


if __name__ == "__main__":
    main()

# scripts/cleanup_data.py
import json
import os
import imaplib
import email
from datetime import datetime, timedelta
from dateutil import parser  # More flexible date parsing

RESULTS_FILE = "data/results.json"
DATA_RETENTION = 35
EMAIL_RETENTION = 10

# Email configuration (same as fetch_emails.py)
zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")
IMAP_SERVER = "imap.zoho.eu"


def load_results():
    """Load test results from the JSON file"""
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found: {RESULTS_FILE}")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results):
    """Save results back to the JSON file"""
    # Create a directory if it doesn't exist
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def filter_old_records(results, days=DATA_RETENTION):
    """Filter out records older than specified days"""
    # Create a timezone-aware cutoff date
    cutoff_date = datetime.now().astimezone() - timedelta(days=days)
    filtered_results = []
    removed_count = 0

    for record in results:
        start = record.get("start") or record.get("end")
        if not start:
            continue

        try:
            # Use dateutil.parser for more robust date parsing
            record_date = parser.isoparse(start)

            if record_date >= cutoff_date:
                filtered_results.append(record)
            else:
                removed_count += 1

        except (ValueError, TypeError) as e:
            print(f"⚠️ Could not parse date '{start}': {e}. Keeping record to be safe.")
            filtered_results.append(record)

    return filtered_results, removed_count


def get_all_mailboxes(mail):
    """Get list of all mailboxes/folders"""
    try:
        status, mailbox_list = mail.list()
        if status != "OK":
            print("❌ Failed to list mailboxes")
            return []

        mailboxes = []
        for mailbox in mailbox_list:
            # Parse mailbox name from response
            mailbox_info = mailbox.decode().split(' "/" ')
            if len(mailbox_info) >= 2:
                mailbox_name = mailbox_info[1].strip('"')
                mailboxes.append(mailbox_name)

        return mailboxes
    except Exception as e:
        print(f"❌ Error listing mailboxes: {e}")
        return []


def delete_old_emails_from_mailbox(mail, mailbox_name, days=EMAIL_RETENTION):
    """Delete emails older than specified days from a specific mailbox"""
    try:
        # Select mailbox
        status, _ = mail.select(mailbox_name)
        if status != "OK":
            print(f"⚠️ Could not select mailbox: {mailbox_name}")
            return 0

        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

        # Search for emails older than cutoff date
        # IMAP date format: "BEFORE 15-May-2026"
        search_criteria = f"BEFORE {cutoff_date}"
        status, data = mail.uid("search", None, search_criteria)

        if status != "OK":
            print(f"⚠️ Search failed in {mailbox_name}")
            return 0

        uids = data[0].split()
        if not uids:
            return 0

        deleted_count = 0
        for uid in uids:
            try:
                # Mark for deletion
                mail.uid("STORE", uid, "+FLAGS", "(\Deleted)")
                deleted_count += 1
            except Exception as e:
                print(f"⚠️ Failed to mark email {uid.decode()} for deletion: {e}")

        # Expunge to actually delete marked emails
        mail.expunge()

        print(f"🗑️ Deleted {deleted_count} emails from {mailbox_name}")
        return deleted_count

    except Exception as e:
        print(f"❌ Error processing mailbox {mailbox_name}: {e}")
        return 0


def cleanup_old_emails():
    """Delete emails older than EMAIL_RETENTION days from all mailboxes"""
    if not all([zoho_user, zoho_pass]):
        print("❌ ZOHO_EMAIL or ZOHO_APP_PASSWORD not set - skipping email cleanup")
        return

    try:
        print("📧 Starting email cleanup...")

        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(zoho_user, zoho_pass)
        print(f"📧 Connected to {IMAP_SERVER} as {zoho_user}")

        # Get all mailboxes
        mailboxes = get_all_mailboxes(mail)
        if not mailboxes:
            print("⚠️ No mailboxes found")
            mail.logout()
            return

        print(f"📧 Found {len(mailboxes)} mailboxes: {', '.join(mailboxes)}")

        total_deleted = 0

        # Process each mailbox
        for mailbox in mailboxes:
            deleted = delete_old_emails_from_mailbox(mail, mailbox, EMAIL_RETENTION)
            total_deleted += deleted

        mail.logout()

        print(f"🗑️ Email cleanup completed: {total_deleted} emails deleted older than {EMAIL_RETENTION} days")

    except Exception as e:
        print(f"❌ Email cleanup error: {e}")


def cleanup_old_data():
    """Main cleanup function to remove records older than 35 days and old emails"""
    try:
        print("🧹 Starting data cleanup...")

        # Load current results
        results = load_results()
        if not results:
            print("⏭️ No data to clean up")
            return

        original_count = len(results)
        print(f"📊 Total records before cleanup: {original_count}")

        # Filter out records older than 35 days
        filtered_results, removed_count = filter_old_records(results, days=DATA_RETENTION)

        # Save filtered results
        save_results(filtered_results)

        print(f"🗑️ Removed {removed_count} records older than {DATA_RETENTION} days")
        print(f"📊 Total records after cleanup: {len(filtered_results)}")

        # Clean up old emails
        cleanup_old_emails()

        print("✅ Data cleanup completed successfully")

    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        raise


if __name__ == "__main__":
    cleanup_old_data()
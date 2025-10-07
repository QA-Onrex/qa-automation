import imaplib
import email
import os

zoho_user = os.getenv("ZOHO_EMAIL")
zoho_pass = os.getenv("ZOHO_APP_PASSWORD")

print(f"Connecting to Zoho IMAP as {zoho_user}...")

mail = imaplib.IMAP4_SSL("imap.zoho.eu")
mail.login(zoho_user, zoho_pass)
mail.select("INBOX")

result, data = mail.search(None, "UNSEEN")
mail_ids = data[0].split()

print(f"Found {len(mail_ids)} unseen emails.")
mail.logout()

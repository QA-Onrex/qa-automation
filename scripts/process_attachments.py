import os
import zipfile
import io
import traceback
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from encryptor import decrypt_file_to_bytes, encrypt_bytes_to_file

ATTACHMENTS_FOLDER = "data/attachments"
HTML_FOLDER = "data/html"
os.makedirs(HTML_FOLDER, exist_ok=True)

def extract_html_from_encrypted_zip(encrypted_zip_path, html_folder):
    """Decrypt an encrypted ZIP, extract the first HTML, re-encrypt HTML in memory, save it."""
    try:
        # Decrypt ZIP into memory
        zip_bytes = decrypt_file_to_bytes(encrypted_zip_path)
        if zip_bytes is None:
            print(f"::error::Failed to decrypt {encrypted_zip_path}")
            return None

        # Open ZIP from memory
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            html_files = [f for f in z.namelist() if f.lower().endswith(".html")]
            if not html_files:
                print(f"::warning::No HTML file found in {encrypted_zip_path}")
                return None

            html_file_in_zip = html_files[0]
            html_filename = os.path.splitext(os.path.basename(encrypted_zip_path))[0] + ".html"
            html_path = os.path.join(html_folder, html_filename)

            # Read HTML bytes from ZIP in memory
            with z.open(html_file_in_zip) as src:
                html_bytes = src.read()

            # Encrypt HTML bytes in memory and write to HTML_FOLDER
            encrypt_bytes_to_file(html_bytes, html_path)
            print(f"::notice::Extracted and encrypted {html_filename} from {os.path.basename(encrypted_zip_path)}")

        return html_path

    except Exception as e:
        print(f"::error::Failed to process {encrypted_zip_path}: {e}")
        traceback.print_exc()
        return None

def main():
    encrypted_zip_files = [f for f in os.listdir(ATTACHMENTS_FOLDER) if f.lower().endswith(".zip")]
    if not encrypted_zip_files:
        print("::notice::No encrypted ZIP files to process.")
        return

    password = os.getenv("REPORT_PASSWORD")
    if not password:
        print("::error::REPORT_PASSWORD not set — cannot decrypt ZIPs.")
        return

    for zip_file in encrypted_zip_files:
        zip_path = os.path.join(ATTACHMENTS_FOLDER, zip_file)
        html_path = extract_html_from_encrypted_zip(zip_path, HTML_FOLDER)
        if html_path:
            # Only delete ZIP after successful extraction
            os.remove(zip_path)
            print(f"::notice::Deleted {zip_file} after extraction")

if __name__ == "__main__":
    main()

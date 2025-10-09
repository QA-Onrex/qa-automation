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

def extract_and_encrypt_html(zip_path, html_folder):
    """Decrypt ZIP, extract first HTML, encrypt HTML, and save it."""
    try:
        # Decrypt ZIP into memory
        zip_bytes = decrypt_file_to_bytes(zip_path)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            html_files = [f for f in z.namelist() if f.lower().endswith(".html")]
            if not html_files:
                print(f"::warning::No HTML file found in {zip_path}")
                return None

            html_file_in_zip = html_files[0]
            html_filename = os.path.splitext(os.path.basename(zip_path))[0] + ".html"
            html_path = os.path.join(html_folder, html_filename)

            # Extract HTML into memory
            with z.open(html_file_in_zip) as src:
                html_bytes = src.read()

            # Encrypt HTML and save
            encrypt_bytes_to_file(html_bytes, html_path)
            print(f"::notice::Extracted & encrypted {html_filename} from {os.path.basename(zip_path)}")
            return html_path

    except Exception as e:
        print(f"::error::Failed to process {zip_path}: {e}")
        traceback.print_exc()
        return None

def main():
    zip_files = [f for f in os.listdir(ATTACHMENTS_FOLDER) if f.lower().endswith(".zip")]
    if not zip_files:
        print("::notice::No ZIP files to process.")
        return

    for zip_file in zip_files:
        zip_path = os.path.join(ATTACHMENTS_FOLDER, zip_file)
        html_path = extract_and_encrypt_html(zip_path, HTML_FOLDER)
        if html_path:
            # Delete encrypted ZIP after successful extraction
            os.remove(zip_path)
            print(f"::notice::Deleted {zip_file} after extraction")

if __name__ == "__main__":
    main()

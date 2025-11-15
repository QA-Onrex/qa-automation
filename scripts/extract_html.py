# scripts/netlify/extract_html.py
import os
import zipfile
import io
import traceback
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scripts.encryptor import decrypt_file_to_bytes, encrypt_bytes_to_file

ATTACHMENTS_FOLDER = "data/netlify_attachments"
HTML_FOLDER = "data/html"

os.makedirs(HTML_FOLDER, exist_ok=True)


def extract_html_from_encrypted_zip(encrypted_zip_path, html_folder):
    """Decrypt ZIP, extract first HTML file, and encrypt HTML for storage"""
    try:
        # Decrypt the encrypted ZIP file into memory
        zip_bytes = decrypt_file_to_bytes(encrypted_zip_path)
        if zip_bytes is None:
            print(f"Failed to decrypt {encrypted_zip_path}")
            return None

        # Open ZIP archive from memory bytes
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # Find all HTML files in the ZIP
            html_files = [f for f in z.namelist() if f.lower().endswith(".html")]
            if not html_files:
                print(f"No HTML file found in {encrypted_zip_path}")
                return None

            # Create output filename and path
            html_file_in_zip = html_files[0]
            html_filename = os.path.splitext(os.path.basename(encrypted_zip_path))[0] + ".html"
            html_path = os.path.join(html_folder, html_filename)

            # Read HTML content from ZIP
            with z.open(html_file_in_zip) as src:
                html_bytes = src.read()

            # Encrypt HTML content and save to output folder
            encrypt_bytes_to_file(html_bytes, html_path)
            print(f"Extracted and encrypted: {html_filename} from {os.path.basename(encrypted_zip_path)}")

        return html_path

    except Exception as e:
        print(f"Failed to process {encrypted_zip_path}: {e}")
        traceback.print_exc()
        return None


def main():
    # Validate required environment variable
    password = os.getenv("REPORT_PASSWORD")
    if not password:
        print("❌ REPORT_PASSWORD not set - cannot decrypt ZIPs")
        sys.exit(1)

    try:
        # Find all encrypted ZIP files in attachments folder
        encrypted_zip_files = [f for f in os.listdir(ATTACHMENTS_FOLDER) if f.lower().endswith(".zip")]
        
        # Exit early if no ZIP files found
        if not encrypted_zip_files:
            print("::notice::⏭️ ZIP files found: 0")
            return

        # Output annotation for found ZIP files
        print(f"::notice::📦 ZIP files found: {len(encrypted_zip_files)}")

        processed_count = 0
        
        # Process each encrypted ZIP file
        for zip_file in encrypted_zip_files:
            zip_path = os.path.join(ATTACHMENTS_FOLDER, zip_file)
            print(f"Processing ZIP file: {zip_file}")
            
            # Extract and encrypt HTML from ZIP
            html_path = extract_html_from_encrypted_zip(zip_path, HTML_FOLDER)
            if html_path:
                # Delete original ZIP after successful extraction
                os.remove(zip_path)
                processed_count += 1
                print(f"Deleted original ZIP: {zip_file}")

        # Output annotation for processed files
        print(f"::notice::✅ HTML files extracted: {processed_count}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

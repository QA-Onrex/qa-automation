import os
import zipfile
import io
import traceback
from encryptor import encrypt_bytes_to_file

ATTACHMENTS_FOLDER = "data/attachments"
HTML_FOLDER = "data/html"
os.makedirs(HTML_FOLDER, exist_ok=True)

def extract_html_from_zip(zip_path, html_folder, password):
    """Extract the first HTML file from a ZIP file, encrypt it, and save to html_folder."""
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            html_files = [f for f in z.namelist() if f.lower().endswith(".html")]
            if not html_files:
                print(f"::warning::No HTML file found in {zip_path}")
                return None

            html_file_in_zip = html_files[0]
            html_filename = os.path.splitext(os.path.basename(zip_path))[0] + ".html"
            html_path = os.path.join(html_folder, html_filename)

            # Read HTML in memory
            with z.open(html_file_in_zip) as src:
                html_bytes = src.read()

            # Encrypt HTML in memory and save
            encrypt_bytes_to_file(html_bytes, html_path, password)
            print(f"::notice::Extracted and encrypted {html_filename} from {os.path.basename(zip_path)}")
            return html_path

    except Exception as e:
        print(f"::error::Failed to extract HTML from {zip_path}: {e}")
        traceback.print_exc()
        return None

def main():
    encrypt_password = os.getenv("REPORT_PASSWORD", "")
    if not encrypt_password:
        print("::error::REPORT_PASSWORD not set — cannot encrypt HTML files.")
        return

    zip_files = [f for f in os.listdir(ATTACHMENTS_FOLDER) if f.lower().endswith(".zip")]
    if not zip_files:
        print("::notice::No ZIP files to process.")
        return

    for zip_file in zip_files:
        zip_path = os.path.join(ATTACHMENTS_FOLDER, zip_file)
        html_path = extract_html_from_zip(zip_path, HTML_FOLDER, encrypt_password)
        if html_path:
            # Only delete ZIP after successful extraction
            os.remove(zip_path)
            print(f"::notice::Deleted {zip_file} after extraction")

if __name__ == "__main__":
    main()

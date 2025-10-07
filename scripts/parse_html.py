
import os
import json
import shutil
import traceback
from bs4 import BeautifulSoup

HTML_FOLDER = "data/html"
PROCESSED_FOLDER = os.path.join(HTML_FOLDER, "processed")
RESULTS_FILE = "data/results.json"
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Load existing results.json
results = []
if os.path.exists(RESULTS_FILE):
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print("::warning::results.json is empty or invalid, starting fresh.")
        results = []

def parse_project_field(html_path):
    """Parse the Project field from HTML using text search."""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Find the span containing "Project:"
        label_span = soup.find(lambda tag: tag.name=="span" and "Project:" in tag.text)
        if label_span and label_span.next_sibling:
            value_span = label_span.next_sibling
            # In case it's nested
            if hasattr(value_span, "text"):
                return value_span.text.strip()
            else:
                return str(value_span).strip()
        else:
            print(f"::warning::Project field not found in {html_path}")
            return None
    except Exception as e:
        print(f"::error::Failed to parse HTML {html_path}: {e}")
        traceback.print_exc()
        return None

def main():
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.lower().endswith(".html")]
    if not html_files:
        print("::notice::No HTML files to process.")
        return

    for html_file in html_files:
        html_path = os.path.join(HTML_FOLDER, html_file)
        try:
            project = parse_project_field(html_path)

            results.append({
                "html_file": f"data/html/processed/{html_file}",  # link will point to processed folder
                "project": project
            })

            # Move processed HTML to processed folder
            shutil.move(html_path, os.path.join(PROCESSED_FOLDER, html_file))
            print(f"::notice::Processed {html_file} and moved to processed folder.")

        except Exception as e:
            print(f"::error::Error processing HTML {html_file}: {e}")
            traceback.print_exc()

    # Save results.json
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"::notice::Updated {RESULTS_FILE} with {len(html_files)} entries.")

if __name__ == "__main__":
    main()

# scripts/netlify/netlify_version_manager.py
import json
import os
from datetime import datetime
import sys

# Output file path for the dashboard to read
VERSION_FILE = "docs/version.json"

def update_dashboard_version():
    """
    Creates or updates the docs/version.json file with the current Unix timestamp.
    This acts as a signal for the frontend to auto-refresh.
    """
    try:
        # Unix timestamp for simple comparison in JavaScript
        version_content = {
            "version": int(datetime.now().timestamp())
        }
        
        # Ensure output folder exists
        os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)

        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(version_content, f)

        print(f"✅ Dashboard version file updated: {version_content['version']}")
        
    except Exception as e:
        print(f"❌ Error updating dashboard version file: {e}")
        # Allow the process to continue even if this step fails
        

if __name__ == "__main__":
    # If run directly (e.g., for testing), execute the update
    update_dashboard_version()

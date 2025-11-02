# scripts/netlify/netlify_archive_manager.py
import json
import os
from datetime import datetime, timedelta

DASHBOARD_DATA_FILE = "docs/dashboard_data.json"
ARCHIVE_FOLDER = "docs/archive"
ARCHIVE_INDEX_FILE = os.path.join(ARCHIVE_FOLDER, "archive_index.json")


def load_dashboard_data():
    """Load current dashboard data"""
    if not os.path.exists(DASHBOARD_DATA_FILE):
        print(f"Dashboard data file not found: {DASHBOARD_DATA_FILE}")
        return None
    
    with open(DASHBOARD_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_dashboard_data(dashboard_data):
    """Validate dashboard data structure"""
    try:
        required_fields = ["data", "dates", "last_updated"]
        for field in required_fields:
            if field not in dashboard_data:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check if there's at least some data
        if not dashboard_data["data"]:
            print("❌ No data in dashboard")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Archive validation error: {e}")
        return False


def update_archive_index(archive_date):
    """Update the archive index with new archive date"""
    index = load_archive_index()
    
    # Add new archive date if not already present
    if archive_date not in index:
        index.append(archive_date)
        index.sort(reverse=True)  # Most recent first
        
        # Save updated index
        with open(ARCHIVE_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        
        print(f"📋 Archive index updated with: {archive_date}")


def load_archive_index():
    """Load existing archive index or create new one"""
    if os.path.exists(ARCHIVE_INDEX_FILE):
        with open(ARCHIVE_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def create_monthly_archive():
    """Create monthly archive of dashboard data"""
    try:
        print("📁 Starting monthly archive creation...")
        
        # Check if it's the 1st of the month
        today = datetime.now()
        if today.day != 1:
            print("⏭️ Not the 1st of month - skipping archive")
            return
        
        # Load current dashboard data
        dashboard_data = load_dashboard_data()
        if not dashboard_data:
            print("❌ No dashboard data to archive")
            return
        
        # Validate data before archiving
        if not validate_dashboard_data(dashboard_data):
            print("❌ Dashboard data validation failed - skipping archive")
            return
        
        # Create archive for previous month
        archive_date = (today - timedelta(days=1)).strftime("%Y_%m")  # Previous month
        archive_file = os.path.join(ARCHIVE_FOLDER, f"{archive_date}_dashboard_data.json")
        
        # Ensure archive folder exists
        os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
        
        # Save archive
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        # Update archive index
        update_archive_index(archive_date)
        
        print(f"✅ Monthly archive created: {archive_file}")
        
    except Exception as e:
        print(f"❌ Archive creation error: {e}")
        raise


if __name__ == "__main__":
    create_monthly_archive()

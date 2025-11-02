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
        print(f"❌ Dashboard data file not found: {DASHBOARD_DATA_FILE}")
        return None
    
    try:
        with open(DASHBOARD_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✅ Loaded dashboard data from: {DASHBOARD_DATA_FILE}")
        return data
    except Exception as e:
        print(f"❌ Error loading dashboard data: {e}")
        return None


def filter_data_by_month(dashboard_data, target_month):
    """Filter dashboard data to only include records from the target month"""
    try:
        filtered_data = {"data": {}, "dates": [], "last_updated": dashboard_data.get("last_updated", "")}
        target_year_month = target_month.replace("_", ".")  # Convert "2025_10" to "2025.10"
        
        records_kept = 0
        records_removed = 0
        
        # Filter data by project and suite
        for project, suites in dashboard_data.get("data", {}).items():
            filtered_data["data"][project] = {}
            
            for suite, dates in suites.items():
                filtered_data["data"][project][suite] = {}
                
                for date_str, record_data in dates.items():
                    # Check if date belongs to target month
                    if date_str.startswith(target_year_month):
                        filtered_data["data"][project][suite][date_str] = record_data
                        records_kept += len(record_data.get("sessions", []))
                    else:
                        records_removed += len(record_data.get("sessions", []))
        
        # Filter dates list
        filtered_data["dates"] = [date for date in dashboard_data.get("dates", []) 
                                 if date.startswith(target_year_month)]
        
        print(f"📊 Data filtering: {records_kept} sessions kept, {records_removed} sessions removed")
        print(f"📅 Dates in archive: {len(filtered_data['dates'])} days from {target_year_month}")
        
        return filtered_data
        
    except Exception as e:
        print(f"❌ Error filtering data by month: {e}")
        return None


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
            
        print("✅ Dashboard data validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Archive validation error: {e}")
        return False


def load_archive_index():
    """Load existing archive index or create new one"""
    if os.path.exists(ARCHIVE_INDEX_FILE):
        try:
            with open(ARCHIVE_INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)
            print(f"✅ Loaded archive index with {len(index)} entries")
            return index
        except Exception as e:
            print(f"❌ Error loading archive index: {e}")
            return []
    else:
        print("📋 No existing archive index found - creating new one")
        return []


def update_archive_index(archive_date):
    """Update the archive index with new archive date"""
    try:
        index = load_archive_index()
        
        # Add new archive date if not already present
        if archive_date not in index:
            index.append(archive_date)
            index.sort(reverse=True)  # Most recent first
            
            # Ensure archive folder exists
            os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
            
            # Save updated index
            with open(ARCHIVE_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
            
            print(f"📋 Archive index updated with: {archive_date}")
            print(f"📊 Total archive entries: {len(index)}")
        else:
            print(f"⏭️ Archive {archive_date} already exists in index")
            
        return index
        
    except Exception as e:
        print(f"❌ Error updating archive index: {e}")
        return []


def get_previous_month():
    """Get the previous month in YYYY_MM format"""
    today = datetime.now()
    
    # If current month is January, previous month is December of previous year
    if today.month == 1:
        previous_month = today.replace(year=today.year - 1, month=12)
    else:
        previous_month = today.replace(month=today.month - 1)
    
    return previous_month.strftime("%Y_%m")


def create_monthly_archive():
    """Create monthly archive of dashboard data for previous month"""
    try:
        print("📁 Starting monthly archive creation...")
        
        # Always create archive for previous month regardless of current date
        archive_date = get_previous_month()
        archive_file = os.path.join(ARCHIVE_FOLDER, f"{archive_date}_dashboard_data.json")
        
        # Check if archive already exists
        if os.path.exists(archive_file):
            print(f"⏭️ Archive for {archive_date} already exists - skipping")
            return
        
        print(f"📅 Creating archive for previous month: {archive_date}")
        
        # Load current dashboard data
        dashboard_data = load_dashboard_data()
        if not dashboard_data:
            print("❌ No dashboard data to archive")
            return
        
        # Filter data to only include records from the target month
        filtered_data = filter_data_by_month(dashboard_data, archive_date)
        if not filtered_data:
            print("❌ No data found for the target month")
            return
        
        # Update last_updated to reflect archive creation time
        filtered_data["last_updated"] = f"Archived on {(datetime.now() + timedelta(hours=1)).strftime('%d/%m/%Y, %H:%M:%S (GMT+1)')}"
        
        # Validate data before archiving
        if not validate_dashboard_data(filtered_data):
            print("❌ Archive data validation failed - skipping archive")
            return
        
        # Ensure archive folder exists
        os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
        
        # Save archive
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, indent=2, default=str)
        
        print(f"💾 Archive saved: {archive_file}")
        
        # Update archive index
        update_archive_index(archive_date)
        
        print(f"✅ Monthly archive created successfully: {archive_date}")
        
    except Exception as e:
        print(f"❌ Archive creation error: {e}")
        raise


if __name__ == "__main__":
    create_monthly_archive()

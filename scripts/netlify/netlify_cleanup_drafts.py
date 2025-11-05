# scripts/netlify/netlify_cleanup_drafts.py
import os
import requests
from datetime import datetime, timedelta
import sys

# Configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")

# ⚙️ CONFIGURATION - Adjust this value as needed
DAYS_TO_KEEP_DRAFTS = 2  # Delete draft deploys older than 7 days

if not NETLIFY_SITE_ID or not NETLIFY_AUTH_TOKEN:
    print("❌ NETLIFY_SITE_ID or NETLIFY_AUTH_TOKEN not set")
    sys.exit(1)


def get_draft_deploys():
    """Fetch all draft deploys from Netlify"""
    headers = {
        "Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    deploys = response.json()
    draft_deploys = [deploy for deploy in deploys if deploy.get("draft")]
    
    print(f"📋 Found {len(deploys)} total deploys, {len(draft_deploys)} are drafts")
    return draft_deploys


def is_older_than_days(deploy, days):
    """Check if deploy is older than specified days"""
    created_at = deploy.get("created_at")
    if not created_at:
        return False
        
    # Parse the date string from Netlify API
    deploy_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    cutoff_date = datetime.now().replace(tzinfo=deploy_date.tzinfo) - timedelta(days=days)
    
    return deploy_date < cutoff_date


def delete_deploy(deploy_id):
    """Delete a specific deploy by ID"""
    headers = {
        "Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}",
    }
    
    url = f"https://api.netlify.com/api/v1/deploys/{deploy_id}"
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 204:
        print(f"✅ Successfully deleted deploy: {deploy_id}")
        return True
    else:
        print(f"❌ Failed to delete deploy {deploy_id}: HTTP {response.status_code}")
        return False


def main():
    print(f"🧹 Netlify Draft Deploy Cleanup")
    print(f"📅 Keeping drafts from the last {DAYS_TO_KEEP_DRAFTS} days")
    print(f"🔍 Site ID: {NETLIFY_SITE_ID}")
    
    try:
        # Get all draft deploys
        draft_deploys = get_draft_deploys()
        
        if not draft_deploys:
            print("🎉 No draft deploys found to clean up")
            return
        
        # Filter old draft deploys
        old_drafts = [deploy for deploy in draft_deploys if is_older_than_days(deploy, DAYS_TO_KEEP_DRAFTS)]
        
        if not old_drafts:
            print(f"🎉 No draft deploys older than {DAYS_TO_KEEP_DRAFTS} days found")
            return
        
        print(f"🗑️  Found {len(old_drafts)} draft deploys older than {DAYS_TO_KEEP_DRAFTS} days")
        
        # Delete old draft deploys
        success_count = 0
        for deploy in old_drafts:
            deploy_id = deploy.get("id")
            created_at = deploy.get("created_at", "unknown")
            print(f"🚮 Deleting draft deploy {deploy_id} from {created_at}")
            
            if delete_deploy(deploy_id):
                success_count += 1
        
        print(f"📊 Cleanup completed: {success_count}/{len(old_drafts)} draft deploys deleted")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Netlify API HTTP Error: {e.response.status_code} - {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

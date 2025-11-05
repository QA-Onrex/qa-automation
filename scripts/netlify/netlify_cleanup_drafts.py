# scripts/netlify/netlify_cleanup_drafts.py
import os
import requests
from datetime import datetime, timedelta
import sys

# Configuration
NETLIFY_SITE_ID = os.getenv("NETLIFY_SITE_ID")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
DAYS_TO_KEEP_DRAFTS = 2  # Delete deploy previews older than 2 days

if not NETLIFY_SITE_ID or not NETLIFY_AUTH_TOKEN:
    print("❌ NETLIFY_SITE_ID or NETLIFY_AUTH_TOKEN not set")
    sys.exit(1)


def get_deploy_previews():
    """Fetch all deploy previews from Netlify"""
    headers = {"Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}"}
    url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    deploys = response.json()
    preview_deploys = [deploy for deploy in deploys if deploy.get("context") == "deploy-preview"]
    
    print(f"::notice::📋 Found {len(deploys)} total deploys, {len(preview_deploys)} are deploy previews")
    return preview_deploys


def is_older_than_days(deploy, days):
    """Check if deploy is older than specified days"""
    created_at = deploy.get("created_at")
    if not created_at:
        return False
        
    deploy_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    cutoff_date = datetime.now().replace(tzinfo=deploy_date.tzinfo) - timedelta(days=days)
    return deploy_date < cutoff_date


def delete_deploy(deploy_id):
    """Delete a specific deploy by ID"""
    headers = {"Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}"}
    url = f"https://api.netlify.com/api/v1/deploys/{deploy_id}"
    response = requests.delete(url, headers=headers)
    return response.status_code == 204


def main():
    try:
        preview_deploys = get_deploy_previews()
        
        if not preview_deploys:
            return
        
        old_deploys = [deploy for deploy in preview_deploys if is_older_than_days(deploy, DAYS_TO_KEEP_DRAFTS)]
        
        if not old_deploys:
            return
        
        print(f"::notice::🗑️  Found {len(old_deploys)} draft deploys older than {DAYS_TO_KEEP_DRAFTS} days")
        
        success_count = 0
        for deploy in old_deploys:
            if delete_deploy(deploy.get("id")):
                success_count += 1
        
        print(f"::notice::📊 Cleanup completed: {success_count}/{len(old_deploys)} draft deploys deleted")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

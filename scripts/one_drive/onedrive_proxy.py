#!/usr/bin/env python3
# scripts/one_drive/onedrive_proxy.py
import os
import requests
from urllib.parse import quote
from flask import Flask, request, Response, session, jsonify
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# OneDrive configuration
ONEDRIVE_REPORTS_FOLDER = "qa-automation/data/reports"

def get_onedrive_access_token():
    """Get access token using refresh token"""
    client_id = os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("ONEDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise Exception("OneDrive credentials missing")
    
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'https://graph.microsoft.com/Files.ReadWrite offline_access'
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get('access_token')
    else:
        raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

def download_from_onedrive_to_memory(file_path, access_token):
    """Download a file from OneDrive directly to memory"""
    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    safe_path = quote(file_path)
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{safe_path}:/content"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        print(f"❌ Failed to download {file_path}: {response.status_code}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user for the proxy"""
    password = request.json.get('password')
    expected_password = os.getenv("REPORT_PASSWORD")
    
    if password == expected_password:
        session['authenticated'] = True
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Invalid password"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.pop('authenticated', None)
    return jsonify({"success": True})

@app.route('/api/report/<path:filename>')
@login_required
def serve_report(filename):
    """Serve HTML reports from OneDrive through proxy"""
    try:
        # Security: Basic path validation
        if '..' in filename or filename.startswith('/'):
            return "Invalid filename", 400
            
        if not filename.lower().endswith('.html'):
            return "Only HTML files allowed", 400
        
        # Get OneDrive access token
        access_token = get_onedrive_access_token()
        
        # Download from OneDrive
        file_path = f"{ONEDRIVE_REPORTS_FOLDER}/{filename}"
        content = download_from_onedrive_to_memory(file_path, access_token)
        
        if content:
            return Response(
                content,
                mimetype='text/html',
                headers={
                    'Content-Disposition': f'inline; filename="{filename}"',
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            )
        else:
            return "Report not found", 404
            
    except Exception as e:
        print(f"❌ Proxy error serving {filename}: {e}")
        return "Internal server error", 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # For production, use: waitress-serve --host=0.0.0.0 --port=5000 onedrive_proxy:app
    app.run(host='0.0.0.0', port=5000, debug=False)

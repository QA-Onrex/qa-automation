# .github/workflows/manage-onedrive-token.yml
name: 🔑 Get OneDrive Token

on:
  workflow_dispatch:

jobs:
  get-token:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: pip install requests
      
    - name: Exchange code for token
      env:
        ONEDRIVE_CLIENT_ID: ${{ secrets.ONEDRIVE_CLIENT_ID }}
        ONEDRIVE_TENANT_ID: ${{ secrets.ONEDRIVE_TENANT_ID }}
        ONEDRIVE_AUTH_CODE: ${{ secrets.ONEDRIVE_AUTH_CODE }}
      run: |
        echo "🔄 Exchanging authorization code for refresh token..."
        
        # Simple Python script to exchange the code
        python3 -c "
        import requests
        import os
        
        tenant_id = os.getenv('ONEDRIVE_TENANT_ID')
        client_id = os.getenv('ONEDRIVE_CLIENT_ID')
        auth_code = os.getenv('ONEDRIVE_AUTH_CODE')
        
        if not all([tenant_id, client_id, auth_code]):
            print('❌ Missing required environment variables')
            exit(1)
        
        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        data = {
            'client_id': client_id,
            'code': auth_code,
            'redirect_uri': 'http://localhost:8080',
            'grant_type': 'authorization_code',
            'scope': 'https://graph.microsoft.com/Files.ReadWrite'
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            tokens = response.json()
            refresh_token = tokens.get('refresh_token')
            print('🎉 SUCCESS! Copy this token to your GitHub Secrets:')
            print('=' * 60)
            print(f'ONEDRIVE_REFRESH_TOKEN = {refresh_token}')
            print('=' * 60)
            print('')
            print('📝 Instructions:')
            print('1. Go to Repository Settings → Secrets → Actions')
            print('2. Update ONEDRIVE_REFRESH_TOKEN with the value above')
            print('3. Delete the ONEDRIVE_AUTH_CODE secret (optional)')
            print('4. Your automation is now ready!')
        else:
            print(f'❌ Failed: {response.status_code}')
            print(f'Error: {response.text}')
        "

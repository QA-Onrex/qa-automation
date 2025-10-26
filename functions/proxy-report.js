// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const filePath = url.searchParams.get('path');
    
    console.log('Proxy request received for file path:', filePath);
    
    if (!filePath) {
      return new Response('Missing file path parameter', { status: 400 });
    }

    // Get OneDrive access token
    const accessToken = await getOneDriveAccessToken(context);
    if (!accessToken) {
      return new Response('Failed to get OneDrive access token', { status: 500 });
    }

    // Download file from OneDrive using Graph API
    const userEmail = 'velko.ikonomov@ncb.global'; // Replace with your email if different
    const safePath = encodeURIComponent(filePath);
    const graphUrl = `https://graph.microsoft.com/v1.0/users/${userEmail}/drive/root:/${safePath}:/content`;
    
    console.log('Fetching from Graph API:', graphUrl);
    
    const response = await fetch(graphUrl, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    console.log('Graph API response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.log('Graph API error response:', errorText);
      return new Response(`Graph API error: ${response.status} - ${response.statusText}`, { 
        status: response.status 
      });
    }

    const html = await response.text();
    console.log('Successfully fetched HTML, length:', html.length);
    
    // Return the HTML with proper headers
    return new Response(html, {
      headers: {
        'Content-Type': 'text/html',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=3600'
      }
    });
    
  } catch (error) {
    console.log('Proxy error:', error.message);
    return new Response(`Proxy error: ${error.message}`, { status: 500 });
  }
}

async function getOneDriveAccessToken(context) {
  try {
    const clientId = context.env.ONEDRIVE_CLIENT_ID;
    const clientSecret = context.env.ONEDRIVE_CLIENT_SECRET;
    const refreshToken = context.env.ONEDRIVE_REFRESH_TOKEN;
    
    if (!clientId || !clientSecret || !refreshToken) {
      console.error('Missing OneDrive environment variables');
      return null;
    }

    const tokenUrl = 'https://login.microsoftonline.com/common/oauth2/v2.0/token';
    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        refresh_token: refreshToken,
        grant_type: 'refresh_token',
        scope: 'https://graph.microsoft.com/Files.ReadWrite offline_access'
      })
    });

    if (!response.ok) {
      console.error('Token refresh failed:', response.status, await response.text());
      return null;
    }

    const tokens = await response.json();
    return tokens.access_token;
  } catch (error) {
    console.error('Token error:', error);
    return null;
  }
}

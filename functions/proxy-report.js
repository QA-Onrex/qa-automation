// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const encryptedUrl = url.searchParams.get('url');
    
    if (!encryptedUrl) {
      return new Response('Missing URL parameter', { status: 400 });
    }

    // Fetch the HTML from OneDrive
    const response = await fetch(encryptedUrl);
    
    if (!response.ok) {
      return new Response(`Failed to fetch from OneDrive: ${response.status}`, { 
        status: response.status 
      });
    }

    const html = await response.text();
    
    // Return the HTML with proper headers
    return new Response(html, {
      headers: {
        'Content-Type': 'text/html',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=3600' // Cache for 1 hour
      }
    });
    
  } catch (error) {
    return new Response(`Proxy error: ${error.message}`, { status: 500 });
  }
}

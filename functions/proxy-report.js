// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const encryptedUrl = url.searchParams.get('url');
    
    console.log('Proxy request received for URL:', encryptedUrl);
    
    if (!encryptedUrl) {
      return new Response('Missing URL parameter', { status: 400 });
    }

    // Fetch the HTML from OneDrive
    console.log('Fetching from OneDrive...');
    const response = await fetch(encryptedUrl);
    
    console.log('OneDrive response status:', response.status);
    console.log('OneDrive response headers:', Object.fromEntries(response.headers));
    
    if (!response.ok) {
      const errorText = await response.text();
      console.log('OneDrive error response:', errorText);
      return new Response(`OneDrive error: ${response.status} - ${response.statusText}\nDetails: ${errorText}`, { 
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

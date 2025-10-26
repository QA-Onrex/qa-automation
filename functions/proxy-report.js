// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const encryptedUrl = url.searchParams.get('url');
    
    console.log('Proxy request received for encrypted URL');
    
    if (!encryptedUrl) {
      return new Response('Missing encrypted URL parameter', { status: 400 });
    }

    // The URL is already decrypted by the dashboard, just use it directly
    console.log('Fetching from decrypted OneDrive URL...');
    const response = await fetch(encryptedUrl);
    
    console.log('OneDrive response status:', response.status);
    
    if (!response.ok) {
      // If we get 403, the sharing link might have expired or have restrictions
      const errorText = await response.text();
      console.log('OneDrive error details:', errorText);
      
      if (response.status === 403) {
        return new Response(
          'OneDrive access forbidden. The sharing link may have expired or have viewing restrictions. ' +
          'Please check that the link is still valid and accessible.', 
          { status: 403 }
        );
      }
      
      return new Response(`OneDrive error: ${response.status} - ${response.statusText}`, { 
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

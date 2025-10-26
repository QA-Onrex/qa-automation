// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const encryptedUrl = url.searchParams.get('url');
    
    console.log('Proxy request received for encrypted URL');
    
    if (!encryptedUrl) {
      return new Response('Missing encrypted URL parameter', { status: 400 });
    }

    // Simulate a browser request to bypass OneDrive blocking
    console.log('Fetching from OneDrive with browser headers...');
    const response = await fetch(encryptedUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
      }
    });
    
    console.log('OneDrive response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.log('OneDrive error details:', errorText.substring(0, 500)); // Limit log size
      
      return new Response(
        `OneDrive access failed (${response.status}): The sharing link may not allow automated access. ` +
        'Please check the link permissions in OneDrive.',
        { status: response.status }
      );
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

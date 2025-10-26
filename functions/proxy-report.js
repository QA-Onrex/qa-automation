// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const encryptedUrl = url.searchParams.get('url');
    
    console.log('Proxy request for OneDrive URL');
    
    if (!encryptedUrl) {
      return new Response('Missing URL parameter', { status: 400 });
    }

    // Create a more realistic browser request
    const browserHeaders = {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'Accept-Language': 'en-US,en;q=0.9',
      'Accept-Encoding': 'gzip, deflate, br',
      'Cache-Control': 'no-cache',
      'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"macOS"',
      'sec-fetch-dest': 'document',
      'sec-fetch-mode': 'navigate',
      'sec-fetch-site': 'cross-site',
      'upgrade-insecure-requests': '1'
    };

    console.log('Making browser-like request to:', encryptedUrl.substring(0, 100) + '...');
    
    const response = await fetch(encryptedUrl, {
      headers: browserHeaders,
      // Add redirect handling
      redirect: 'follow'
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers));
    
    if (!response.ok) {
      // Try to get more error info
      const errorBody = await response.text();
      console.log('Error response body (first 200 chars):', errorBody.substring(0, 200));
      
      return new Response(
        `OneDrive blocked the request (${response.status}). This is likely because OneDrive detects automated access.`,
        { status: response.status }
      );
    }

    const html = await response.text();
    console.log('Success! HTML length:', html.length);
    
    return new Response(html, {
      headers: {
        'Content-Type': 'text/html',
        'Access-Control-Allow-Origin': '*'
      }
    });
    
  } catch (error) {
    console.log('Proxy error:', error.message);
    return new Response(`Proxy error: ${error.message}`, { status: 500 });
  }
}

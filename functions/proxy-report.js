// functions/proxy-report.js
export async function onRequest(context) {
  try {
    const url = new URL(context.request.url);
    const encryptedUrl = url.searchParams.get('url');
    
    console.log('=== PROXY DEBUG ===');
    console.log('Full encrypted URL received:', encryptedUrl);
    
    if (!encryptedUrl) {
      return new Response('Missing URL parameter', { status: 400 });
    }

    // Log the exact URL we're trying to fetch
    console.log('Fetching from this exact URL:', encryptedUrl);
    
    const browserHeaders = {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    };

    const response = await fetch(encryptedUrl, { headers: browserHeaders });
    
    console.log('Response status:', response.status);
    console.log('Response OK?', response.ok);
    
    if (!response.ok) {
      const errorBody = await response.text();
      console.log('Error response:', errorBody.substring(0, 500));
      return new Response(`OneDrive error: ${response.status} - ${response.statusText}`, { 
        status: response.status 
      });
    }

    const html = await response.text();
    console.log('Success! HTML length:', html.length);
    console.log('First 200 chars of HTML:', html.substring(0, 200));
    
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

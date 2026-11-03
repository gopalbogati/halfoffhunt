// Site is private for now: every request needs the owner's login (HTTP Basic Auth).
// Only the SHA-256 of "user:password" lives here; the password is in the owner's macOS Keychain
// (service "halfoffhunt.pages.dev"). To make the site public again, delete this file and redeploy.
const AUTH_SHA256 = '9a38f1573571d3703ae6bf63fcfa6fbe3a5e3060b619393405dc7da008d94f93';

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function onRequest({ request, next }) {
  const header = request.headers.get('Authorization') || '';
  if (header.startsWith('Basic ')) {
    let decoded = '';
    try { decoded = atob(header.slice(6)); } catch (_) { /* bad base64 falls through to 401 */ }
    if (decoded && (await sha256Hex(decoded)) === AUTH_SHA256) {
      const response = await next();
      const res = new Response(response.body, response);
      res.headers.set('X-Robots-Tag', 'noindex, nofollow');
      res.headers.set('Cache-Control', 'private, no-store');
      return res;
    }
  }
  return new Response('This site is private.', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Half Off Hunt (private)", charset="UTF-8"',
      'X-Robots-Tag': 'noindex, nofollow',
      'Cache-Control': 'no-store',
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}

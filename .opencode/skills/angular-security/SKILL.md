---
name: Angular Security
description: Harden Angular apps against XSS, unsafe DOM APIs, token theft, open redirects, and supply-chain risk with sanitization, CSP, Trusted Types, OIDC, guards, interceptors, and secure SSR. Use when handling untrusted content, auth, or production security review.
---

# Angular Security

Angular prevents most XSS by escaping values in templates and sanitizing bound
HTML, styles, and URLs. The remaining risk is code that deliberately bypasses
those protections, leaks credentials, or trusts the client for authorization.

## Threat model first

- The client is hostile territory. Anything shipped to the browser can be read
  and modified.
- The server enforces authentication and authorization. Guards improve UX; they
  are not a security boundary.
- Treat all user input, URL parameters, API responses, and third-party scripts as
  untrusted.
- The highest-impact frontend risks are XSS, token theft, open redirects, and a
  compromised dependency.

## XSS and sanitization

```ts
// Safe: Angular escapes interpolation.
template: `<p>{{ comment }}</p>`;

// Safe: Angular sanitizes the HTML value.
template: `<div [innerHTML]="commentHtml"></div>`;

// Dangerous: bypasses sanitization. Only for trusted, static content.
this.sanitizer.bypassSecurityTrustHtml(vettedHtml);
```

Rules:

- Prefer text interpolation. Do not render user HTML.
- `[innerHTML]` is sanitized, but still avoid it for rich user content; use a
  server-side sanitizer and a strict allowlist if you must.
- Never pass user input to `bypassSecurityTrustHtml`, `bypassSecurityTrustStyle`,
  `bypassSecurityTrustScript`, `bypassSecurityTrustUrl`, or
  `bypassSecurityTrustResourceUrl`.
- If a bypass is unavoidable, wrap it in one audited utility with a comment
  explaining the source and why it is trusted.
- Do not use `ElementRef.nativeElement.innerHTML`, `outerHTML`, `document.write`,
  `eval`, `new Function`, or string `setTimeout`.
- Do not build URLs from user input without validating the scheme and host.
- Angular sanitizes `javascript:` URLs in `href`/`src`; do not disable that by
  bypassing.
- Sanitize on the server too. A client-side sanitizer protects the client only.

## Content Security Policy

CSP is the strongest defense after escaping. Start with a strict policy and
allowlist only what the app actually needs.

```jsonc
// angular.json
"security": {
  "autoCsp": true
}
```

`autoCsp` generates a hash-based strict CSP for inline scripts in `index.html`
and can enable Trusted Types. It is the Angular CLI's built-in starting point;
confirm its status in the installed version and still set headers at the server
or CDN.

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-<random>' 'strict-dynamic';
  style-src 'self' 'nonce-<random>';
  img-src 'self' data: https://cdn.example.com;
  font-src 'self';
  connect-src 'self' https://api.example.com;
  object-src 'none';
  base-uri 'self';
  frame-ancestors 'none';
  form-action 'self';
  upgrade-insecure-requests;
  report-uri /csp-report;
```

- Avoid `'unsafe-inline'` and `'unsafe-eval'`. They defeat most of CSP's value.
- Prefer nonces or hashes over host allowlists.
- `frame-ancestors` and `report-uri` must be set as headers; a `<meta>` CSP
  cannot enforce them.
- Roll out with `Content-Security-Policy-Report-Only`, fix violations, then
  enforce.
- A CSP that allows every third-party tag manager is mostly decoration.

## Trusted Types

Angular supports Trusted Types. Enable it to turn DOM XSS sinks into typed
boundaries.

```http
Content-Security-Policy:
  require-trusted-types-for 'script';
  trusted-types angular;
```

- Add your own policy names only if you create trusted values deliberately.
- Test in report-only mode first; violations reveal unsafe DOM code.
- Do not add `'allow-duplicates'` or a permissive default policy to silence
  errors.

## Authentication

Use the OIDC Authorization Code flow with PKCE through a maintained library.

```ts
// Conceptual provider configuration
provideAuth({
  config: {
    authority: 'https://login.example.com',
    clientId: 'web-app',
    redirectUrl: `${location.origin}/auth/callback`,
    postLogoutRedirectUri: `${location.origin}/`,
    scope: 'openid profile email offline_access',
    responseType: 'code',
    silentRenew: true,
    useRefreshToken: true,
    secureRoutes: ['https://api.example.com/'],
  },
});
```

- Never use the implicit flow. Never ship a client secret.
- Validate `iss`, `aud`, `exp`, `iat`, `nonce`, and state. The library should do
  this; verify it does.
- Keep access tokens in memory. Prefer a refresh token in an `HttpOnly`,
  `Secure`, `SameSite` cookie managed by the backend over `localStorage`.
- `localStorage` is readable by any XSS. If you must use it, minimize token
  lifetime and treat XSS prevention as critical.
- Do not put tokens in URLs, query strings, logs, analytics, or error reports.
- Implement logout that clears local state and revokes the session where
  supported.
- Handle session expiry with a re-authentication flow, not a silent failure.

## Authorization

```ts
export const authGuard: CanActivateFn = () => {
  const auth = inject(Auth);
  const router = inject(Router);
  return auth.isAuthenticated() ? true : router.createUrlTree(['/login']);
};
```

- Guards decide what to render; the API decides what is allowed.
- Check object-level permissions on the server for every read and write.
- Do not hide a feature and assume it is protected. A user can call the API
  directly.
- Do not encode roles in the client bundle as the source of truth.
- Return `404` rather than leaking existence when that matches the product's
  security policy.

## HTTP and CSRF

```ts
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(Auth).accessToken();
  const authorized = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;
  return next(authorized);
};
```

- Use the built-in XSRF support (`withXsrfConfiguration`) for cookie-based
  sessions; the server must validate the token.
- Send credentials only to trusted origins. Never set
  `withCredentials: true` for a wildcard API.
- Validate redirect targets against an allowlist to prevent open redirects.
- Set request timeouts and handle cancellation.
- Do not log request bodies, headers, or tokens. Redact at the logger.

## SSR security

- Never expose server secrets, environment variables, or internal URLs in the
  client bundle or transfer state.
- Treat SSR as a public server: validate input, rate-limit, set security
  headers, and sanitize rendered content.
- Isolate per-request state. A module-level singleton that holds user data leaks
  across requests.
- Do not proxy arbitrary URLs from the server without an allowlist; that is
  SSRF.
- Trust proxy headers only behind a proxy you control.
- Disable or protect source maps in production; upload them privately to error
  tracking.

## Third-party code and supply chain

- Self-host critical scripts when possible and use Subresource Integrity for
  CDN scripts.
- Every third-party script is code with full access to the page. Review it and
  keep it out of authenticated areas when you can.
- Commit the lockfile; use `npm ci` in CI.
- Run `npm audit --omit=dev` and triage advisories.
- Use Renovate/Dependabot for updates; review major bumps and postinstall
  scripts.
- Prefer packages with provenance and active maintenance. Watch for typosquats.
- Do not add a dependency for a one-line utility.

## Headers

Set these at the server or CDN:

```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
X-Frame-Options: DENY
```

`X-Frame-Options` is superseded by CSP `frame-ancestors`, but keep both for older
clients if needed.

## postMessage and embeds

```ts
window.addEventListener('message', (event) => {
  if (event.origin !== 'https://trusted.example.com') return;
  if (event.source !== iframe.contentWindow) return;
  handle(event.data);
});
```

- Always check `event.origin` against an exact allowlist.
- Validate the message shape before using it.
- When sending, set an explicit `targetOrigin`, never `'*'` with sensitive data.
- Sandbox iframes you do not fully trust.

## Anti-patterns

- Rendering user HTML with `bypassSecurityTrustHtml`.
- `innerHTML`, `eval`, or `new Function` on untrusted data.
- Secrets or long-lived tokens in the client bundle or `localStorage`.
- Client-side authorization treated as enforcement.
- Guards that only hide routes but do not protect API calls.
- `allow_origins=['*']` with credentials on the API.
- CSP with `'unsafe-inline'` and `'unsafe-eval'`.
- Disabling TLS verification or trusting all proxy headers.
- Third-party scripts without review or SRI.
- Tokens in URLs, logs, or analytics.
- `postMessage` handlers without an origin check.
- Open redirects from an unvalidated `returnUrl`.

## Checklist

- [ ] Untrusted data is rendered through interpolation or sanitized bindings.
- [ ] No `bypassSecurityTrust*` on user input; any bypass is audited.
- [ ] No `innerHTML`, `eval`, or `new Function` on untrusted data.
- [ ] A strict CSP is deployed and monitored in report-only before enforcement.
- [ ] Trusted Types are enabled where the browser support matrix allows.
- [ ] OIDC uses Authorization Code + PKCE; no client secret is shipped.
- [ ] Tokens are short-lived and stored as safely as the backend allows.
- [ ] Guards are UX; the server enforces every authorization decision.
- [ ] CSRF protection matches the session model.
- [ ] Redirect targets and `postMessage` origins are validated.
- [ ] SSR exposes no secrets and keeps per-request state isolated.
- [ ] Security headers are set at the edge.
- [ ] Dependencies are locked, audited, and reviewed.
- [ ] Logs and error reports redact tokens and PII.

## References

- `references/security-checklist.md` — CSP, Trusted Types, interceptor, OIDC,
  sanitizer wrapper, and header recipes.

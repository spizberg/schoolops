# Security recipes

## Strict CSP with nonces

Server-rendered `index.html` must receive a fresh nonce per response. With SSR
or a templating layer, inject it into the document head.

```html
<meta
  http-equiv="Content-Security-Policy"
  content="default-src 'self'; script-src 'self' 'nonce-{{nonce}}' 'strict-dynamic'; style-src 'self' 'nonce-{{nonce}}'; img-src 'self' data: https://cdn.example.com; connect-src 'self' https://api.example.com; object-src 'none'; base-uri 'self'; form-action 'self'"
/>
```

Headers can enforce directives that `<meta>` cannot:

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-<random>' 'strict-dynamic'; style-src 'self' 'nonce-<random>'; img-src 'self' data: https://cdn.example.com; connect-src 'self' https://api.example.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; report-uri /csp-report
```

Roll out:

```http
Content-Security-Policy-Report-Only: <same policy>
```

Collect reports, fix inline scripts and unsafe DOM code, then switch to
enforcement.

## Angular CLI auto-CSP

```jsonc
// angular.json
{
  "projects": {
    "web": {
      "architect": {
        "build": {
          "options": {
            "security": { "autoCsp": true }
          }
        }
      }
    }
  }
}
```

This generates a hash-based policy for inline scripts in `index.html`. It does
not replace server headers or cover your API's CORS policy. Check the installed
CLI version for the exact schema and whether Trusted Types are included.

## Trusted Types

```http
Content-Security-Policy: require-trusted-types-for 'script'; trusted-types angular
```

- Test in report-only mode.
- Fix violations by removing unsafe DOM sinks, not by creating a permissive
  policy.
- If you create a custom policy, keep it tiny and audited:

```ts
if (window.trustedTypes) {
  const policy = trustedTypes.createPolicy('app-static-html', {
    createHTML: (input: string) => sanitizeWithServerAllowlist(input),
  });
  element.innerHTML = policy.createHTML(staticTemplate);
}
```

Prefer Angular bindings over this path.

## Sanitizer wrapper

```ts
import { Injectable, inject } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Injectable({ providedIn: 'root' })
export class TrustedContent {
  private readonly sanitizer = inject(DomSanitizer);

  /**
   * Only for HTML produced by our CMS after server-side sanitization.
   * Never pass user input or API content that has not been sanitized.
   */
  cmsHtml(html: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}
```

Keep every bypass in a file like this with an explicit trust statement and a
test that proves the source is controlled.

## Auth interceptor with safe logging

```ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Auth } from './auth';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(Auth).accessToken();

  const authorized = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authorized);
};
```

Do not log `req.headers`. If you need request telemetry, record the method,
route template, status, and duration only.

## OIDC configuration

```ts
import { provideAuth } from 'angular-auth-oidc-client';

export const authConfig = provideAuth({
  config: {
    authority: 'https://login.example.com',
    clientId: 'web-app',
    redirectUrl: `${window.location.origin}/auth/callback`,
    postLogoutRedirectUri: `${window.location.origin}/`,
    scope: 'openid profile email offline_access',
    responseType: 'code',
    silentRenew: true,
    useRefreshToken: true,
    secureRoutes: ['https://api.example.com/'],
    renewTimeBeforeTokenExpiresInSeconds: 30,
  },
});
```

- Verify the library validates issuer, audience, nonce, and state.
- Keep the client public. PKCE replaces the client secret.
- Prefer a backend-for-frontend that holds refresh tokens in `HttpOnly` cookies.
- Configure auth in the browser bootstrap; on the server, derive the origin from
  the request rather than reading `location`.
- Clear tokens and cached user data on logout.

## Route guard and return URL

```ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from './auth';

export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(Auth);
  const router = inject(Router);

  if (auth.isAuthenticated()) return true;

  const returnUrl = state.url.startsWith('/') ? state.url : '/';
  return router.createUrlTree(['/login'], { queryParams: { returnUrl } });
};
```

Validate `returnUrl` on the login page before navigating:

```ts
const target = this.route.snapshot.queryParamMap.get('returnUrl');
const safeTarget = target && target.startsWith('/') && !target.startsWith('//')
  ? target
  : '/';
await this.router.navigateByUrl(safeTarget);
```

Reject absolute URLs and protocol-relative URLs.

## CSRF

For cookie-based sessions, configure the built-in XSRF handling:

```ts
provideHttpClient(
  withFetch(),
  withXsrfConfiguration({
    cookieName: 'XSRF-TOKEN',
    headerName: 'X-XSRF-TOKEN',
  }),
);
```

The server must set the cookie and validate the header. SameSite cookies are a
useful additional layer, not a replacement for token validation.

## SSR request isolation

```ts
// Wrong: shared across requests.
let currentUser: User | null = null;

// Right: no providedIn. Provide it in the server's per-request injector.
@Injectable()
export class UserContext {
  private readonly user = signal<User | null>(null);
  set(user: User): void { this.user.set(user); }
  clear(): void { this.user.set(null); }
}
```

With SSR, `providedIn: 'root'` services are shared across requests on the server.
Create request-scoped providers in the server bootstrap or pass user context
explicitly. Never store request data in module-level variables.

## Security headers at the edge

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;
add_header X-Frame-Options "DENY" always;
```

Replace the CSP placeholder with the policy from the top of this file.

## Dependency audit

```sh
npm ci
npm audit --omit=dev
npm outdated
```

- Triage advisories by reachability, not only severity.
- Pin the lockfile and review lockfile diffs in pull requests.
- Reject packages with unexpected `postinstall` scripts unless reviewed.
- Prefer packages with signed provenance and active maintenance.

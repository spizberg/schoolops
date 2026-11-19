---
name: Angular Deployment
description: Ship Angular apps with production builds, runtime config, Docker, nginx or CDN caching, SSR hosting, security headers, observability, feature flags, and rollback. Use when preparing a release, writing a Dockerfile, or debugging a deployment.
---

# Angular Deployment

A production build is not a deployment. You also need configuration that does
not change per build, caching that cannot serve stale HTML, headers that protect
users, and a way to roll back.

## Build

```sh
ng build --configuration production
```

- Use the application builder (`@angular/build`). Webpack builders are
  deprecated in v22.
- Production builds hash assets and minify by default. Do not disable hashing.
- Keep source maps out of public responses; upload them privately to error
  tracking.
- Fail the build on budget violations. A warning that is ignored is not a budget.
- Build once and promote the same artifact through environments. Do not rebuild
  per environment unless the configuration is genuinely build-time.

```text
dist/web/
├── browser/     # static assets, index.html
└── server/      # server.mjs when SSR is enabled
```

## Configuration

- Build-time values (`production: true`, feature flags baked at build) belong in
  `environment.ts`.
- Per-environment values (API URL, tenant, analytics key) belong in a runtime
  `config.json` fetched before bootstrap.
- Never ship secrets. The client bundle is public.
- Validate runtime config on load and fail fast with a visible error.
- Set `Cache-Control: no-cache` on `config.json` so a deploy can change it
  without a new bundle.

```json
{
  "apiBaseUrl": "https://api.example.com",
  "environment": "production",
  "analyticsKey": "public-write-only-key"
}
```

## Static hosting and caching

| Asset | Cache policy |
| --- | --- |
| `index.html` | `no-cache` or short max-age, revalidate |
| Hashed JS/CSS/fonts | `public, max-age=31536000, immutable` |
| `config.json` | `no-cache` |
| Images with content hashes | `public, max-age=31536000, immutable` |
| Service worker | `no-cache` |
| API responses | Per endpoint; never cache authenticated data publicly |

- Serve `index.html` for unknown routes in a client-side routed app
  (`try_files $uri $uri/ /index.html;`).
- Do not cache `index.html` at the CDN without a purge strategy. Users will get
  old chunk references and a blank page.
- Deploy assets before HTML, or keep old hashed chunks available during the
  rollout.
- Compress with Brotli and gzip at the CDN or server.

## Docker for a static app

```dockerfile
# build
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# serve
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/web/browser /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://localhost/healthz || exit 1
```

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;

  location = /healthz {
    access_log off;
    add_header Content-Type text/plain;
    return 200 'ok';
  }

  location = /index.html {
    add_header Cache-Control "no-cache";
  }

  location = /config.json {
    add_header Cache-Control "no-cache";
  }

  location ~* \.(?:js|css|woff2?|png|jpg|jpeg|svg|avif|webp)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
  }

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

Add the security headers from `angular-security` at this layer.

## SSR hosting

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist/web ./dist/web
COPY package*.json ./
RUN npm ci --omit=dev
EXPOSE 4000
CMD ["node", "dist/web/server/server.mjs"]
```

- Run the generated Node server behind a reverse proxy or platform that handles
  TLS, compression, and timeouts.
- Set `PORT`, `HOST`, and any server-only secrets through the environment.
- Never expose server-only env vars to the client bundle or transfer state.
- Keep the Node process alive and healthy; add a `/healthz` route and a
  readiness check.
- Handle graceful shutdown: stop accepting connections, finish in-flight
  requests, close pools.
- Cache SSR HTML at the CDN only when the response is not user-specific.
- Scale horizontally; do not rely on in-memory session state.
- Pin the Node major to the one you test.

## Reverse proxy and timeouts

- Set connect, read, and send timeouts.
- Cap request body size.
- Forward the correct `Host`, `X-Forwarded-Proto`, and client IP only from a
  trusted proxy.
- Enable HTTP/2 or HTTP/3 at the edge.
- Redirect HTTP to HTTPS and send HSTS.

## Observability

- Capture uncaught errors with Sentry or an equivalent; upload source maps
  privately.
- Record Core Web Vitals with RUM, not only lab tests.
- Log structured events with route, status, duration, and release version. Never
  log tokens, bodies, or PII.
- Add a release identifier to every event and error.
- Alert on error rate, latency, and availability, not on CPU alone.
- Add a health endpoint that checks only what the process needs to serve
  traffic. Deep dependency checks belong in readiness.

## Releases and rollback

- Version the release and expose it in a meta tag or health response.
- Use feature flags for risky behavior so you can disable it without a deploy.
- Prefer canary or staged rollout for SSR and infrastructure changes.
- Keep the previous artifact deployable. Rollback must be one command.
- Invalidate the CDN cache for `index.html` and `config.json` after a deploy.
- If you use a service worker, ship an update strategy and test the upgrade
  path. A stale service worker can pin users to an old app.
- Run migrations before the app serves traffic, with a rollback plan.

## CI/CD pipeline

```text
install → format/lint/typecheck → unit tests → build → e2e → deploy staging
→ smoke test → promote production → verify → rollback on failure
```

- Build once; promote the artifact.
- Run E2E against the deployed staging URL, not only locally.
- Smoke test the production URL after promotion: health, home, login, one API
  call.
- Do not deploy from an untrusted branch.
- Require approvals for production and keep an audit trail.

## Anti-patterns

- Rebuilding per environment with different code.
- Secrets in the bundle or in `environment.ts`.
- Caching `index.html` for a year.
- Serving old HTML that references deleted chunks.
- Running `ng serve` in production.
- SSR without a health check, timeouts, or graceful shutdown.
- Storing sessions in process memory behind a load balancer.
- Deploying without a rollback path.
- Source maps publicly accessible.
- Ignoring budget failures.
- No cache invalidation on deploy.
- Monitoring only the server, not real user metrics.

## Checklist

- [ ] Production build uses the application builder and passes budgets.
- [ ] Source maps are private and uploaded to error tracking.
- [ ] Runtime config is validated, cache-busted, and contains no secrets.
- [ ] Hashed assets are immutable; `index.html` and `config.json` revalidate.
- [ ] Unknown routes fall back to `index.html` for client routing.
- [ ] Security headers and HTTPS are enforced at the edge.
- [ ] SSR has health checks, timeouts, graceful shutdown, and no shared request
      state.
- [ ] Errors and Core Web Vitals are monitored with a release identifier.
- [ ] Feature flags, canary, and rollback are documented.
- [ ] CDN cache is purged on deploy.
- [ ] Staging smoke tests cover health, home, auth, and one API call.
- [ ] The previous artifact can be restored in one command.

## References

- `references/deployment-recipes.md` — Dockerfiles, nginx, runtime config,
  SSR server, cache headers, and a CI/CD pipeline.

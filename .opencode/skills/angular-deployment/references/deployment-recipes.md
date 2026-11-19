# Deployment recipes

## Production build

```sh
npm ci
npm run check
ng build --configuration production
```

Output:

```text
dist/web/
├── browser/
│   ├── index.html
│   ├── main-<hash>.js
│   ├── styles-<hash>.css
│   └── assets/
└── server/
    └── server.mjs        # only with SSR
```

## Runtime config loader

```ts
// src/app/core/config/app-config.ts
import { InjectionToken } from '@angular/core';

export interface AppConfig {
  apiBaseUrl: string;
  environment: 'staging' | 'production';
  analyticsKey?: string;
}

export const APP_CONFIG = new InjectionToken<AppConfig>('APP_CONFIG');
```

```ts
// src/app/core/config/load-config.ts
import { AppConfig } from './app-config';

export async function loadConfig(): Promise<AppConfig> {
  const response = await fetch('/config.json', { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Config failed: ${response.status}`);

  const value: unknown = await response.json();
  if (!isAppConfig(value)) throw new Error('Invalid config.json');
  return value;
}

function isAppConfig(value: unknown): value is AppConfig {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v['apiBaseUrl'] === 'string' &&
    (v['environment'] === 'staging' || v['environment'] === 'production')
  );
}
```

```ts
// main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { appConfig } from './app/app.config';
import { APP_CONFIG } from './app/core/config/app-config';
import { loadConfig } from './app/core/config/load-config';

loadConfig()
  .then((config) =>
    bootstrapApplication(App, {
      providers: [{ provide: APP_CONFIG, useValue: config }, ...appConfig.providers],
    }),
  )
  .catch((error) => {
    console.error(error);
    document.body.textContent = 'The application failed to start. Please reload.';
  });
```

Serve `config.json` with `Cache-Control: no-cache`.

## nginx for a static app

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;

  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
  add_header X-Frame-Options "DENY" always;

  gzip on;
  gzip_types text/css application/javascript application/json image/svg+xml;

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

nginx does not inherit `add_header` into a `location` block that declares its own
`add_header`. Repeat the security headers in those blocks, or set them at the CDN
or load balancer. The cache rules above are the important part of this file.

## Multi-stage Dockerfile for a static app

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/web/browser /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://localhost/healthz || exit 1
```

```sh
docker build -t web:$(git rev-parse --short HEAD) .
docker run --rm -p 8080:80 web:local
```

## Dockerfile for SSR

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

The generated server reads `PORT` (default 4000). Add a health route if the
template does not provide one:

```ts
// server.ts (excerpt)
server.get('/healthz', (_req, res) => res.status(200).send('ok'));
```

Handle shutdown:

```ts
process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
});
```

## CDN cache rules

```text
/index.html          Cache-Control: no-cache
/config.json         Cache-Control: no-cache
/*.js, *.css, fonts  Cache-Control: public, max-age=31536000, immutable
/images/*            Cache-Control: public, max-age=31536000, immutable
/api/*               per endpoint, private for authenticated data
```

On deploy, purge `index.html` and `config.json`. Keep old hashed chunks
available for at least one release window so users with open tabs do not crash.

## Feature flags

```ts
export interface FeatureFlags {
  newCheckout: boolean;
  recommendations: boolean;
}

export const FEATURE_FLAGS = new InjectionToken<FeatureFlags>('FEATURE_FLAGS');
```

```html
@if (flags().newCheckout) {
  <app-new-checkout />
} @else {
  <app-legacy-checkout />
}
```

- Load flags before rendering the affected route.
- Default to the safe, existing behavior when flags fail to load.
- Remove the flag and dead branch after rollout.
- Never use a flag as a security control.

## Release version

```ts
// app.config.ts
providers: [
  { provide: RELEASE, useValue: '2026.11.19-abc1234' },
]
```

Expose it in a meta tag or health response so support can confirm what is
running:

```html
<meta name="release" content="2026.11.19-abc1234" />
```

## Error tracking

```ts
import * as Sentry from '@sentry/angular';

Sentry.init({
  dsn: environment.sentryDsn,
  release: environment.release,
  environment: environment.name,
  tracesSampleRate: 0.1,
  integrations: [Sentry.browserTracingIntegration()],
});
```

- Upload source maps during the build, not at runtime.
- Do not send PII, tokens, or request bodies.
- Set a sampling rate you can afford.
- Tag errors with route and release.

## CI/CD sketch

```yaml
name: deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npm run check
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: web
          path: dist/web

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: web
      - run: ./scripts/deploy.sh
      - run: ./scripts/smoke-test.sh "$PRODUCTION_URL"
```

## Smoke test

```sh
#!/usr/bin/env bash
set -euo pipefail

base_url="${1:?base url required}"

curl -fsS "$base_url/healthz" > /dev/null
curl -fsS "$base_url/" | grep -q '<app-root'
curl -fsS "$base_url/config.json" | grep -q 'apiBaseUrl'
curl -fsS -o /dev/null -w '%{http_code}' "$base_url/login" | grep -q '200'
```

Add an authenticated API check if the app has a public health endpoint for it.

## Rollback

- Keep the last two artifacts tagged and deployable.
- Roll back the app before rolling back the database.
- If a migration is not backward compatible, deploy in expand/contract steps.
- Purge the CDN after rollback so clients get the previous `index.html`.
- Verify the release meta tag after rollback.

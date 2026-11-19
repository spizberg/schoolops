# Performance checklist and recipes

## Budgets

```jsonc
// angular.json
"budgets": [
  { "type": "initial", "maximumWarning": "400kB", "maximumError": "600kB" },
  { "type": "anyComponentStyle", "maximumWarning": "6kB", "maximumError": "10kB" }
]
```

Start from the current baseline plus 5–10%. Lower it as you improve. A budget
that never fires protects nothing.

## Build and inspect

```sh
ng build --configuration production --stats-json
npx esbuild-visualizer --metadata dist/web/stats.json --open
```

```sh
# Per-route sizes in the build output
ng build --configuration production
```

Compare the initial bundle and each lazy chunk before and after a change. Look
for accidental imports of charting, date, icon, or UI libraries.

## Defer patterns

```html
<!-- Below the fold -->
@defer (on viewport) {
  <app-testimonials />
} @placeholder (minimum 300ms) {
  <div class="testimonials-skeleton" aria-hidden="true"></div>
}

<!-- Behind a tab or dialog -->
@defer (on interaction) {
  <app-advanced-filters />
} @placeholder {
  <button type="button">Show advanced filters</button>
}

<!-- Non-critical, after the page is idle -->
@defer (on idle) {
  <app-support-chat />
}

<!-- Prefetch when the user hovers a trigger -->
@defer (on hover; prefetch on idle) {
  <app-reporting-panel />
}
```

- Match placeholder dimensions to the final content to avoid CLS.
- Do not defer the LCP element or the primary call to action.
- Keep deferred components self-contained; they must not depend on providers
  that only exist in the parent route unless that route stays active.

## Images

```html
<picture>
  <source srcset="/hero.avif" type="image/avif" />
  <source srcset="/hero.webp" type="image/webp" />
  <img
    ngSrc="/hero.jpg"
    width="1600"
    height="900"
    priority
    alt="Team reviewing a dashboard"
  />
</picture>
```

```html
<!-- Responsive content image -->
<img
  ngSrc="/product.jpg"
  width="800"
  height="600"
  sizes="(max-width: 600px) 100vw, 50vw"
  alt="Product detail"
/>
```

- `priority` only on the LCP image. Multiple priorities compete.
- Decorative images use `alt=""`, not a missing `alt`.
- Use a CDN that resizes and converts formats; do not ship originals.

## Fonts

```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter-latin.woff2') format('woff2');
  font-weight: 400 700;
  font-display: swap;
  unicode-range: U+0000-00FF;
}
```

```html
<link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin />
```

Preload one file, not every weight. Reserve space with `size-adjust` or a
metric-compatible fallback.

## SSR and hydration

```ts
// app.config.ts
import {
  provideClientHydration,
  withEventReplay,
  withIncrementalHydration,
} from '@angular/platform-browser';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withEventReplay(), withIncrementalHydration()),
    // ...
  ],
};
```

```ts
// Browser-only work
import { afterNextRender, Component, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({ /* ... */ })
export class MapView {
  private readonly platform = inject(PLATFORM_ID);

  constructor() {
    afterNextRender(() => {
      if (isPlatformBrowser(this.platform)) {
        this.initMap();
      }
    });
  }

  private initMap(): void { /* third-party map */ }
}
```

- Never touch `window`, `document`, or `localStorage` at module scope.
- Ensure the same data renders on server and client.
- Cache SSR responses at the CDN when the content is not user-specific.
- Measure time to first byte; SSR that takes 2 seconds loses to static HTML.

## Long lists

```html
<cdk-virtual-scroll-viewport itemSize="72" class="list">
  @for (row of rows(); track row.id) {
    <app-row [row]="row" />
  }
</cdk-virtual-scroll-viewport>
```

```css
.list { height: 480px; }
```

Use virtualization above roughly 100–200 visible rows, or when row rendering is
expensive. Keep `track` stable.

## Change detection audit

- Search for `ChangeDetectorRef`, `NgZone`, `setTimeout`, and `zone.js`.
- Search for function calls in templates that sort, filter, or build objects.
- Search for `track $index` in lists that reorder.
- Search for subscriptions without `takeUntilDestroyed` or cleanup.
- Search for `providedIn: 'root'` stores that hold route data forever.

## Core Web Vitals commands

```sh
# Lab audit (install once)
npx lighthouse http://localhost:4200 --preset=desktop --view
npx lighthouse http://localhost:4200 --form-factor=mobile --throttling-method=simulate --view
```

Use field data from RUM when available. Lab scores are a proxy, not the goal.

## Regression guard

- Run Lighthouse CI on the critical routes in CI.
- Fail on a budget regression, not on a fixed score.
- Track bundle size per pull request.
- Keep a performance budget document with owners and review dates.

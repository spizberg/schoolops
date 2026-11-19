---
name: Angular Performance
description: Optimize Angular apps with zoneless change detection, OnPush, signals, lazy routes, deferrable views, image and font optimization, SSR and hydration, bundle budgets, and Core Web Vitals measurement. Use when an app is slow, bundles grow, or performance needs a budget.
---

# Angular Performance

Performance is a budget you defend, not a cleanup you schedule. Measure first,
fix the largest user-visible cost, and keep it from regressing.

## Measure before changing

- Use Lighthouse or PageSpeed Insights for lab LCP, INP, and CLS.
- Use real-user monitoring (RUM) for field data. Lab data lies about real
  devices and networks.
- Profile with Chrome DevTools Performance for long tasks and main-thread work.
- Inspect the build output for bundle size per route.
- Record a baseline and the target. "Feels faster" is not a result.

## Change detection

Angular 21+ defaults new apps to zoneless change detection; Angular 22 defaults
new components to OnPush.

- Do not add `zone.js` back without a documented reason.
- Update state through signals so the scheduler knows what changed.
- Avoid mutating objects or arrays in place; replace them.
- Do not inject `ChangeDetectorRef` to force updates. Fix the data flow.
- Keep templates cheap: no sorting, filtering, or object creation per render.
- Use `computed()` for derived values instead of template method calls.
- For large lists, use `@for` with a stable `track` and consider virtual
  scrolling from `@angular/cdk/scrolling`.

## Lazy loading

- Lazy-load every feature route with `loadChildren` or `loadComponent`.
- Keep the initial bundle to the shell and the landing route.
- Use `@defer` for below-the-fold and heavy widgets:

```html
@defer (on viewport) {
  <app-revenue-chart [data]="data()" />
} @placeholder (minimum 200ms) {
  <div class="chart-placeholder" aria-hidden="true"></div>
} @loading (minimum 300ms) {
  <app-spinner />
} @error {
  <p role="alert">Chart unavailable.</p>
}
```

- Use `injectAsync` for heavy services that are rarely needed.
- Do not lazy-load the LCP hero, primary navigation, or critical form controls.
- Do not preload every lazy route by default; measure whether it helps.

## Images

Use `NgOptimizedImage` for content images.

```ts
import { NgOptimizedImage } from '@angular/common';

@Component({
  imports: [NgOptimizedImage],
  template: `
    <img
      ngSrc="/hero.avif"
      width="1600"
      height="900"
      priority
      alt="Team collaborating in the studio"
    />
    <img ngSrc="/avatar.jpg" width="64" height="64" alt="" />
  `,
})
export class Hero {}
```

- Always set `width` and `height` (or a fill container) to prevent layout shift.
- Set `priority` on the LCP image only.
- Serve AVIF/WebP with fallbacks; use a CDN that negotiates formats.
- Lazy-load below-the-fold images by default; `NgOptimizedImage` does this.
- Use `srcset`/`sizes` for responsive images. Do not ship a 4000px image to a
  phone.
- Use CSS `background-image` only for decorative images that are not content.

## Fonts

- Self-host or use a CDN with `font-display: swap`.
- Preload the one font used above the fold; do not preload every weight.
- Subset to the languages you support.
- Avoid layout shift by matching fallback metrics or reserving space.
- Limit the number of families and weights.

## SSR and hydration

Add SSR when first paint or crawlability matters. It is not free.

```ts
import { provideClientHydration, withEventReplay, withIncrementalHydration } from '@angular/platform-browser';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withEventReplay(), withIncrementalHydration()),
  ],
};
```

- Hydration reuses server-rendered DOM instead of re-rendering.
- Incremental hydration defers hydrating `@defer` blocks until needed.
- Guard browser APIs with `isPlatformBrowser` or `afterNextRender`.
- Ensure server and client render the same output; mismatches break hydration.
- Use `TransferState` or `httpResource` so the client does not refetch data the
  server already loaded.
- Do not SSR pages that are entirely user-specific and uncacheable unless the
  first paint justifies the cost.
- Measure server response time; slow SSR makes LCP worse.

## Bundle hygiene

- Set initial and component style budgets and keep them tight.
- Run `ng build --stats-json` and inspect with a bundle analyzer before adding a
  dependency.
- Import only what you use. Avoid barrel files that pull whole libraries into a
  route.
- Prefer tree-shakable standalone imports over a module that re-exports
  everything.
- Do not ship polyfills for browsers you do not support.
- Audit large dependencies quarterly; replace or lazy-load them.
- Keep source maps out of production responses, but upload them to error
  tracking.

## Runtime costs

- Avoid memory leaks: clean up subscriptions, timers, observers, and third-party
  instances.
- Use `IntersectionObserver` instead of scroll listeners for visibility.
- Debounce high-frequency input; cancel stale requests.
- Move CPU-heavy work to a Web Worker when it blocks interaction.
- Avoid layout thrashing: batch reads and writes; use `afterNextRender` for
  measurement.
- Cache immutable API responses with proper HTTP headers.
- Do not add a service worker for caching unless offline or installability is a
  requirement; it complicates deploys.

## Core Web Vitals

| Metric | Target | Main levers |
| --- | --- | --- |
| LCP | ≤ 2.5 s | Server response, render-blocking resources, hero image, fonts |
| INP | ≤ 200 ms | Main-thread work, change detection, event handlers, hydration |
| CLS | ≤ 0.1 | Image dimensions, font metrics, injected banners, deferred content |

- Measure on a mid-tier mobile device with throttled CPU and network.
- Optimize the LCP element first; it usually dominates.
- Break long tasks; yield to the main thread for large renders.
- Reserve space for async content to protect CLS.
- Re-measure after each change; one fix can shift the bottleneck.

## Anti-patterns

- Optimizing without a baseline or a target.
- Eagerly importing every feature into the root bundle.
- `zone.js` retained in a zoneless app.
- `ChangeDetectorRef.detectChanges()` as a default fix.
- Template method calls that allocate, sort, or filter.
- `track $index` for reorderable lists.
- Images without dimensions, or a full-size hero on mobile.
- Preloading every font weight.
- SSR enabled with browser globals in constructors.
- Shipping source maps publicly.
- A service worker added without a cache invalidation plan.
- Adding a heavy charting or UI library for one widget.
- Ignoring a budget failure by raising the budget.

## Checklist

- [ ] Baseline and target for LCP, INP, and CLS are recorded.
- [ ] Zoneless change detection is enabled; OnPush is the default.
- [ ] State updates use signals; templates are cheap.
- [ ] Feature routes are lazy-loaded.
- [ ] Heavy below-the-fold content uses `@defer` with a placeholder.
- [ ] Images use `NgOptimizedImage` with dimensions and `priority` only on LCP.
- [ ] Fonts are subset, swapped, and limited.
- [ ] SSR and hydration are configured deliberately, with no browser globals in
      constructors.
- [ ] Bundle budgets are enforced in CI.
- [ ] Large dependencies are justified and monitored.
- [ ] Subscriptions, observers, and timers are cleaned up.
- [ ] Long lists use tracking and virtualization where needed.
- [ ] Performance is re-measured after each optimization.

## References

- `references/performance-checklist.md` — budgets, defer patterns, image and
  SSR config, and measurement commands.

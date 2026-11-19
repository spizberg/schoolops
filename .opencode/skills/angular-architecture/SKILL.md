---
name: Angular Architecture
description: Structure a scalable Angular application with feature boundaries, standalone components, lazy routes, dependency injection, route-level state, and clear ownership. Use when planning an app structure, adding a feature, or reviewing module boundaries.
---

# Angular Architecture

Architecture is the set of boundaries that decide how expensive the next change
will be. Good Angular architecture makes a feature easy to add and hard to couple
to unrelated code.

## Principles

- Organize by feature, not by technical type. `features/orders/` beats
  `services/` plus `components/` plus `models/`.
- Depend inward: features depend on shared and core; core and shared never
  depend on features. Two features never import each other's internals.
- Keep the public surface of a feature small. Export route definitions and a
  small API; keep the rest private.
- Prefer standalone components and functional providers. Do not create NgModules
  for new code.
- Own state at the lowest level that works. Lift it only when two distant
  consumers need it.
- Make the URL carry navigational state: filters, sorting, pagination, and
  selected tabs. It is shareable, bookmarkable, and testable.
- Push I/O to the edge: components render, stores/services fetch and mutate,
  pure functions decide.

## Layout

```text
src/app/
├── app.ts
├── app.html
├── app.config.ts
├── app.routes.ts
├── core/
│   ├── auth/
│   ├── config/
│   ├── http/
│   ├── errors/
│   └── telemetry/
├── shared/
│   ├── ui/
│   ├── directives/
│   └── utils/
├── layout/
│   ├── app-shell/
│   └── page-header/
└── features/
    ├── orders/
    │   ├── orders.routes.ts
    │   ├── data/
    │   │   ├── order-api.ts
    │   │   ├── order-store.ts
    │   │   └── order.model.ts
    │   ├── feature/
    │   │   ├── order-list-page.ts
    │   │   └── order-detail-page.ts
    │   └── ui/
    │       ├── order-card.ts
    │       └── order-status-badge.ts
    └── checkout/
```

- `core/` is imported once and holds singletons and app-wide concerns.
- `shared/` holds generic, reusable pieces with no product knowledge.
- `layout/` holds the shell, navigation, and page chrome.
- `features/<name>/data/` owns models, API access, and state.
- `features/<name>/feature/` owns routed page components.
- `features/<name>/ui/` owns presentational components.
- One feature may expose a narrow `index.ts`. Do not barrel-export everything;
  it hides coupling and hurts tree shaking.

## Bootstrap and routing

```ts
// app.config.ts
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { appRoutes } from './app.routes';
import { authInterceptor } from './core/auth/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection(),
    provideBrowserGlobalErrorListeners(),
    provideRouter(
      appRoutes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled', anchorScrolling: 'enabled' }),
    ),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
  ],
};
```

```ts
// app.routes.ts
import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const appRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./layout/app-shell/app-shell').then((m) => m.AppShell),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'orders' },
      {
        path: 'orders',
        canActivate: [authGuard],
        loadChildren: () => import('./features/orders/orders.routes').then((m) => m.ordersRoutes),
        title: 'Orders',
      },
      {
        path: 'checkout',
        loadChildren: () =>
          import('./features/checkout/checkout.routes').then((m) => m.checkoutRoutes),
        title: 'Checkout',
      },
      { path: '**', loadComponent: () => import('./shared/ui/not-found').then((m) => m.NotFound) },
    ],
  },
];
```

- Lazy-load every feature route. The initial bundle should contain the shell and
  the landing route only.
- Use `loadComponent` for a single page and `loadChildren` for a feature.
- Use functional guards and resolvers. Inject inside them, not through
  constructor parameters.
- Prefer `withComponentInputBinding()` so route params become component inputs.
- Set `title` on routes; update dynamic titles in the page when data arrives.
- Use `canMatch` when a route should not even be considered for a user or
  tenant.
- Keep redirects explicit and terminate with a wildcard route.

## Dependency injection

- Use `inject()` in field initializers. Avoid constructor parameter injection in
  new code.
- `providedIn: 'root'` for true app singletons. In Angular 22, `@Service()` is a
  concise alternative for the same default.
- Use an injection token for configuration and for replacing external
  boundaries (clock, storage, analytics, feature flags).
- Scope a service to a feature route with a route-level `providers` array when
  the state should be discarded on navigation.
- Use `injectAsync` for heavy, rarely used services that should be code-split.
- Never use the injector as a service locator (`inject(SomeService)` inside a
  method is fine; passing the injector around is not).

```ts
// features/orders/orders.routes.ts
import { Routes } from '@angular/router';
import { OrderStore } from './data/order-store';

export const ordersRoutes: Routes = [
  {
    path: '',
    providers: [OrderStore],
    children: [
      { path: '', loadComponent: () => import('./feature/order-list-page').then((m) => m.OrderListPage) },
      { path: ':orderId', loadComponent: () => import('./feature/order-detail-page').then((m) => m.OrderDetailPage) },
    ],
  },
];
```

## Smart and presentational components

| | Routed page (smart) | Presentational |
| --- | --- | --- |
| Knows router | Yes | No |
| Fetches data | Yes, via store/API | No |
| Inputs | Route params, store slices | Plain data and callbacks |
| Outputs | Navigation and commands | User intent only |
| Reusable | Rarely | Yes |
| Tests | Integration | Isolated |

- A presentational component takes data in and emits intent out. It does not
  inject `HttpClient`, `Router`, or a feature store.
- A page component reads route inputs, calls the store, and composes UI.
- If a presentational component needs six inputs to render, it probably wants a
  view model object.
- Do not pass a whole store into a child. Pass the slice and the actions.

## State ownership

```text
Local signal        → one component
Feature store       → one feature, route-scoped when possible
Global store        → cross-cutting session state (auth, tenant, cart)
URL                 → filters, sorting, pagination, deep links
Server cache        → httpResource/resource for reads
```

- Start local. Lift state when a second consumer appears, not before.
- A feature store is a service with private writable signals and public readonly
  signals or computed values.
- Do not create a global store for data only one route uses.
- Keep server state and client state separate. Do not copy a server response
  into a writable signal and let the two drift.
- Treat the URL as the source of truth for list state.

## Errors and resilience

- Register a global `ErrorHandler` for uncaught errors and report them to
  telemetry.
- Use `@boundary` (developer preview in v22) around risky, isolated widgets so a
  failure renders a fallback instead of breaking the page. Verify its status in
  the installed version before depending on it.
- Represent loading, empty, error, and success explicitly. A page that only
  handles success is unfinished.
- Map HTTP failures to user-facing messages at the feature boundary, not in
  every component.
- Retry only idempotent reads, with a bounded backoff. Never retry a mutation
  blindly.

## Naming and file conventions

- Use kebab-case file names: `order-list-page.ts`, `order-store.ts`.
- Match the class name to the file: `OrderListPage` in `order-list-page.ts`.
- Follow the current Angular style guide; do not append `.component.ts` in new
  code.
- Name selectors with the app prefix and feature: `app-order-card`.
- Put one primary export per file. Co-locate the template and styles for
  non-trivial components.
- Keep tests next to the code (`order-store.spec.ts`) unless the project
  centralizes them.

## Anti-patterns

- A `shared/` or `core/` that imports feature code.
- Feature-to-feature imports of internal files.
- One giant `AppModule` or a `SharedModule` that re-exports everything.
- Eagerly importing every feature into the root bundle.
- A global store for state used by one page.
- Passing the router or `HttpClient` into presentational components.
- Route guards treated as security; the server must enforce authorization.
- Duplicating server data into local writable state without a sync strategy.
- Deep barrel files that create import cycles.
- Folder-by-type structure (`components/`, `services/`, `models/`) at scale.
- A route tree with no wildcard or no titles.
- Mutable singleton state shared across SSR requests.

## Checklist

- [ ] Features are self-contained and expose a small public surface.
- [ ] Core and shared do not depend on features.
- [ ] All feature routes are lazy-loaded.
- [ ] Route params and query params are typed and used as state.
- [ ] Guards and resolvers are functional and inject their dependencies.
- [ ] Singletons are `providedIn: 'root'` or `@Service`; feature state is
      route-scoped.
- [ ] Pages fetch and navigate; presentational components only render and emit.
- [ ] State lives at the lowest level that works.
- [ ] Loading, empty, error, and success states are designed.
- [ ] Uncaught errors are reported centrally.
- [ ] File and selector naming follows the current style guide.

## References

- `references/feature-layout.md` — a complete feature with routes, store, page,
  and presentational components.

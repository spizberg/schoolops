---
name: Angular State Management
description: Manage Angular state with signals, computed values, resource and httpResource, service stores, RxJS interop, URL state, caching, optimistic updates, and SSR-safe patterns. Use when deciding where state lives, fetching data, or fixing stale or leaking state.
---

# Angular State Management

State bugs come from unclear ownership. Decide who owns each piece of state,
make reads reactive, and make writes go through one place.

## Choose the smallest tool

| Need | Use |
| --- | --- |
| One component's UI state | `signal()` |
| Derived value | `computed()` |
| Derived writable value | `linkedSignal()` |
| Read from an API, tied to inputs | `httpResource()` |
| Any async read with custom loader | `resource()` |
| Feature state shared by routes/components | Route-scoped service store |
| Cross-cutting session state | Root service store |
| Filters, paging, sort, selected tab | URL query params |
| Streaming or complex event pipelines | RxJS |

Start local. Move state up only when a second consumer needs it. A global store
is a cost, not a default.

## Signals

```ts
import { computed, signal } from '@angular/core';

const items = signal<CartItem[]>([]);
const count = computed(() => items().reduce((sum, item) => sum + item.quantity, 0));
const totalCents = computed(() =>
  items().reduce((sum, item) => sum + item.priceCents * item.quantity, 0),
);
```

Rules:

- `computed()` must be pure. No HTTP, no logging, no mutation.
- Never write to a signal inside `computed()`.
- Use `update()` for transformations of the previous value; `set()` for
  replacements.
- Do not store derived data in its own signal. Derive it.
- `linkedSignal()` is for a writable value that resets when a source changes,
  such as a selected row that resets when the list reloads.
- Keep signals private when they are writable; expose `asReadonly()` or a
  computed.

## Effects

`effect()` is for side effects, not state synchronization.

Good uses:

- Persist a preference to `localStorage`.
- Send analytics when a route or filter changes.
- Call a non-Angular library when a signal changes.

Bad uses:

- Copying `firstName` and `lastName` into `fullName`. Use `computed()`.
- Fetching data. Use `resource`, a resolver, or an explicit method.
- Resetting a form when an input changes. Use `linkedSignal` or a route reload.

Effects run after change detection, can read signals, and should clean up with
`onCleanup`. Avoid writing signals in an effect unless the write is the side
effect you intend.

## Reads with `resource` and `httpResource`

`resource()` and `httpResource()` are stable in Angular 22. They track signal
inputs, cancel stale requests, and expose loading, error, and value states.

```ts
import { Component, input } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { Order } from './order.model';

@Component({
  selector: 'app-order-detail',
  template: `
    @if (order.isLoading()) {
      <p role="status">Loading…</p>
    } @else if (order.error()) {
      <p role="alert">Could not load this order.</p>
    } @else if (order.hasValue()) {
      <h1>Order {{ order.value().id }}</h1>
    }
  `,
})
export class OrderDetail {
  readonly orderId = input.required<string>();

  readonly order = httpResource<Order>(() => `/api/orders/${this.orderId()}`, {
    defaultValue: undefined,
  });
}
```

```ts
import { resource, signal } from '@angular/core';

const city = signal('Chicago');

const forecast = resource({
  params: () => ({ city: city() }),
  loader: async ({ params, abortSignal }) => {
    const response = await fetch(`/api/forecast/${params.city}`, { signal: abortSignal });
    if (!response.ok) throw new Error(`Forecast failed: ${response.status}`);
    return (await response.json()) as Forecast;
  },
});
```

- Use `params` (not `request`) for the reactive input.
- Use the provided `abortSignal` in `fetch` so stale requests are cancelled.
- Check `isLoading()`, `error()`, `hasValue()`, and `status()` explicitly.
- Call `reload()` after a mutation that invalidates the resource.
- Set `defaultValue` only when the UI can render without data.
- Do not use a resource for a command (`POST`, `PUT`, `DELETE`). Use
  `HttpClient` or a store method.

## Service stores

A store is a service that owns feature state. Keep it small and explicit.

```ts
import { computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { OrderApi } from './order-api';
import { Order, OrderFilters } from './order.model';

export class OrderStore {
  private readonly api = inject(OrderApi);

  private readonly ordersState = signal<Order[]>([]);
  private readonly loadingState = signal(false);
  private readonly errorState = signal<string | null>(null);

  readonly orders = this.ordersState.asReadonly();
  readonly loading = this.loadingState.asReadonly();
  readonly error = this.errorState.asReadonly();
  readonly count = computed(() => this.orders().length);

  async load(filters: OrderFilters): Promise<void> {
    this.loadingState.set(true);
    this.errorState.set(null);
    try {
      this.ordersState.set(await firstValueFrom(this.api.list(filters)));
    } catch {
      this.errorState.set('Could not load orders.');
    } finally {
      this.loadingState.set(false);
    }
  }

  async cancel(id: string): Promise<void> {
    const previous = this.ordersState();
    this.ordersState.update((orders) =>
      orders.map((order) => (order.id === id ? { ...order, status: 'cancelled' } : order)),
    );
    try {
      await firstValueFrom(this.api.cancel(id));
    } catch (error) {
      this.ordersState.set(previous);
      throw error;
    }
  }
}
```

- Expose readonly state and intention-revealing methods.
- Keep the API client separate; the store coordinates, it does not build URLs.
- Scope the store to a route when the state should not outlive the feature.
- Do not inject the store into presentational components.

## Optimistic updates

For actions that should feel instant:

1. Snapshot the current state.
2. Apply the expected change.
3. Send the request.
4. On failure, restore the snapshot and surface an error.
5. On success, reconcile with the server response, not with the guess.

Never leave the UI in a state that claims success when the request failed. Show
a retry path.

## RxJS interop

Use RxJS where it earns its keep: debounced typeahead, websockets, complex event
composition, and existing APIs.

```ts
import { toSignal } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';

readonly results = toSignal(
  this.query$.pipe(
    debounceTime(300),
    distinctUntilChanged(),
    switchMap((query) => this.api.search(query)),
  ),
  { initialValue: [] },
);
```

- `toSignal()` for template reads; `toObservable()` when an RxJS operator is
  genuinely needed.
- Use `takeUntilDestroyed()` for subscriptions created in an injection context.
- `switchMap` for cancellable reads, `concatMap` for ordered writes,
  `mergeMap` only with a concurrency limit.
- Never subscribe inside a subscribe. Compose operators.
- Avoid `firstValueFrom` on an observable that may never emit; add a timeout or
  use a finite HTTP observable.

## URL as state

Filters, sorting, pagination, and tabs belong in the URL.

```ts
import { Component, inject, input } from '@angular/core';
import { Router } from '@angular/router';

@Component({ /* ... */ })
export class OrderListPage {
  private readonly router = inject(Router);

  readonly status = input<'all' | 'paid' | 'shipped'>('all');
  readonly page = input(1, { transform: Number });

  setStatus(status: string): void {
    void this.router.navigate([], {
      queryParams: { status, page: 1 },
      queryParamsHandling: 'merge',
    });
  }
}
```

- Read route params through `withComponentInputBinding()` or
  `toSignal(route.queryParamMap)`.
- Write with `queryParamsHandling: 'merge'` so unrelated params survive.
- Validate and clamp params (page >= 1, known status values) at the boundary.
- Do not keep a second copy of URL state in a signal.

## Caching and freshness

- Let HTTP caching headers do their job; do not build a cache for static data.
- Use `httpResource` for request deduplication and cancellation.
- Add an interceptor for auth, correlation IDs, and error normalization, not for
  ad hoc caching.
- For stale-while-revalidate, show cached data with a `stale` flag and refresh
  in the background.
- Invalidate explicitly after mutations. Do not rely on a timer to fix stale
  data.
- For writes, send an idempotency key when the API supports it.

## SSR-safe state

- Never store request-specific data in a module-level singleton. The server
  process handles many requests.
- Use `TransferState` (or `httpResource` with hydration) to avoid refetching on
  the client.
- Guard browser APIs (`window`, `localStorage`, `document`) with
  `isPlatformBrowser` or run them in `afterNextRender`.
- Do not read `Date.now()` or random values during server render if the client
  will render different output; hydration will mismatch.

## Anti-patterns

- `effect()` used to derive state.
- A writable global store for one page's data.
- Duplicating server data into a local signal with no invalidation strategy.
- Subscribing without cleanup.
- Nested subscriptions instead of `switchMap`/`concatMap`.
- Storing `loading` as a boolean when concurrent requests can overlap.
- Retrying mutations automatically.
- Treating `undefined`, empty, and error as the same UI state.
- Keeping filters only in component state, so the back button loses them.
- Reading `localStorage` during SSR.
- Caching without an invalidation rule.

## Checklist

- [ ] Every piece of state has one owner.
- [ ] Derived state uses `computed()`, not a synchronized signal or effect.
- [ ] Reads use `resource`/`httpResource` or a store method with explicit states.
- [ ] Loading, empty, error, and success are all handled.
- [ ] Requests cancel when inputs change or the component is destroyed.
- [ ] Mutations have a rollback path and an idempotency strategy where needed.
- [ ] RxJS subscriptions are cleaned up.
- [ ] List filters, sorting, and paging live in the URL.
- [ ] Feature stores are route-scoped when possible.
- [ ] State is request-scoped under SSR.
- [ ] Caches have an explicit invalidation rule.

## References

- `references/state-recipes.md` — resource, store, optimistic update, typeahead,
  URL filters, and SSR transfer state.

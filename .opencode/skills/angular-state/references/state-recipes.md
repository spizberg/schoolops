# State recipes

## `httpResource` with a signal input

```ts
import { Component, input } from '@angular/core';
import { httpResource } from '@angular/common/http';

interface Order {
  id: string;
  status: 'pending' | 'paid' | 'shipped';
}

@Component({
  selector: 'app-order-detail',
  template: `
    @switch (order.status()) {
      @case ('loading') { <p role="status">Loading…</p> }
      @case ('error') { <p role="alert">Order not found.</p> }
      @case ('resolved') { <h1>Order {{ order.value()!.id }}</h1> }
    }
  `,
})
export class OrderDetail {
  readonly orderId = input.required<string>();
  readonly order = httpResource<Order>(() => `/api/orders/${this.orderId()}`);
}
```

`httpResource` cancels the previous request when `orderId` changes. Use
`order.reload()` after a mutation.

## `resource` with a custom loader and abort

```ts
import { resource, signal } from '@angular/core';

const search = signal('');

const results = resource({
  params: () => ({ q: search().trim() }),
  loader: async ({ params, abortSignal }) => {
    if (!params.q) return [];
    const response = await fetch(`/api/search?q=${encodeURIComponent(params.q)}`, {
      signal: abortSignal,
    });
    if (!response.ok) throw new Error(`Search failed: ${response.status}`);
    return (await response.json()) as SearchResult[];
  },
});
```

The `params` callback is reactive. Returning `undefined` from `params` disables
the resource, which is useful when required inputs are missing.

## Store with optimistic update

```ts
import { computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { TodoApi } from './todo-api';

export interface Todo {
  id: string;
  title: string;
  done: boolean;
}

export class TodoStore {
  private readonly api = inject(TodoApi);

  private readonly todosState = signal<Todo[]>([]);
  private readonly pendingState = signal<ReadonlySet<string>>(new Set());

  readonly todos = this.todosState.asReadonly();
  readonly pending = this.pendingState.asReadonly();
  readonly remaining = computed(() => this.todos().filter((todo) => !todo.done).length);

  async toggle(id: string): Promise<void> {
    const snapshot = this.todosState();
    const target = snapshot.find((todo) => todo.id === id);
    if (!target) return;

    this.markPending(id, true);
    this.todosState.update((todos) =>
      todos.map((todo) => (todo.id === id ? { ...todo, done: !todo.done } : todo)),
    );

    try {
      const saved = await firstValueFrom(this.api.update(id, { done: !target.done }));
      this.todosState.update((todos) => todos.map((todo) => (todo.id === id ? saved : todo)));
    } catch (error) {
      this.todosState.set(snapshot);
      throw error;
    } finally {
      this.markPending(id, false);
    }
  }

  private markPending(id: string, pending: boolean): void {
    this.pendingState.update((current) => {
      const next = new Set(current);
      if (pending) next.add(id);
      else next.delete(id);
      return next;
    });
  }
}
```

A `Set` of pending IDs is safer than a single boolean when requests overlap.

## Typeahead with RxJS

```ts
import { Component, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { SearchApi } from './search-api';

@Component({
  selector: 'app-search',
  template: `
    <input [value]="query()" (input)="query.set($any($event.target).value)" />
    @for (result of results(); track result.id) {
      <a [href]="result.url">{{ result.title }}</a>
    }
  `,
})
export class Search {
  private readonly api = inject(SearchApi);
  readonly query = signal('');

  readonly results = toSignal(
    toObservable(this.query).pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap((query) => this.api.search(query)),
    ),
    { initialValue: [] },
  );
}
```

Import `toObservable` from `@angular/core/rxjs-interop`. `switchMap` cancels the
previous request.

## URL filters with typed inputs

```ts
import { Component, inject, input } from '@angular/core';
import { Router } from '@angular/router';

type Sort = 'created' | 'total';

@Component({ /* ... */ })
export class OrderListPage {
  private readonly router = inject(Router);

  readonly status = input('all', {
    transform: (value: string) =>
      ['all', 'pending', 'paid', 'shipped'].includes(value) ? value : 'all',
  });
  readonly page = input(1, {
    transform: (value: string | number) => Math.max(1, Number(value) || 1),
  });
  readonly sort = input<Sort>('created', {
    transform: (value: string): Sort => (value === 'total' ? 'total' : 'created'),
  });

  update(params: Record<string, string | number>): void {
    void this.router.navigate([], {
      queryParams: params,
      queryParamsHandling: 'merge',
    });
  }
}
```

Route config needs `withComponentInputBinding()`. Invalid values are normalized
before they reach the store.

## SSR transfer state

```ts
import { HttpClient } from '@angular/common/http';
import { isPlatformBrowser } from '@angular/common';
import { Injectable, inject, makeStateKey, PLATFORM_ID, TransferState } from '@angular/core';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

interface Order {
  id: string;
}

const ORDERS_KEY = makeStateKey<Order[]>('orders');

@Injectable({ providedIn: 'root' })
export class OrderBootstrap {
  private readonly http = inject(HttpClient);
  private readonly transfer = inject(TransferState);
  private readonly platform = inject(PLATFORM_ID);

  load(): Observable<Order[]> {
    const cached = this.transfer.get(ORDERS_KEY, null);
    if (cached) return of(cached);

    return this.http.get<Order[]>('/api/orders').pipe(
      tap((orders) => {
        if (!isPlatformBrowser(this.platform)) {
          this.transfer.set(ORDERS_KEY, orders);
        }
      }),
    );
  }
}
```

`httpResource` participates in hydration transfer state automatically when the
app uses `provideClientHydration()`. Use manual `TransferState` for custom
loaders.

## What not to do

```ts
// Wrong: effect synchronizing derived state.
effect(() => this.fullName.set(`${this.first()} ${this.last()}`));

// Right:
readonly fullName = computed(() => `${this.first()} ${this.last()}`);
```

```ts
// Wrong: nested subscriptions.
this.route.params.subscribe((params) => {
  this.api.get(params['id']).subscribe((order) => this.order.set(order));
});

// Right:
readonly order = httpResource<Order>(() => `/api/orders/${this.orderId()}`);
```

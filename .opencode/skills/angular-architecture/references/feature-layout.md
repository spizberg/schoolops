# Feature layout

A worked example of one feature that follows the architecture skill. Replace
`orders` with your domain.

## Tree

```text
src/app/features/orders/
├── orders.routes.ts
├── data/
│   ├── order.model.ts
│   ├── order-api.ts
│   └── order-store.ts
├── feature/
│   ├── order-list-page.ts
│   ├── order-list-page.html
│   └── order-detail-page.ts
└── ui/
    ├── order-card.ts
    └── order-status-badge.ts
```

## Model

```ts
// data/order.model.ts
export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'cancelled';

export interface Order {
  id: string;
  customerName: string;
  status: OrderStatus;
  totalCents: number;
  createdAt: string;
}

export interface OrderFilters {
  status: OrderStatus | 'all';
  page: number;
}
```

## API

```ts
// data/order-api.ts
import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { APP_CONFIG } from '../../../core/config/app-config';
import { Order, OrderFilters } from './order.model';

@Injectable({ providedIn: 'root' })
export class OrderApi {
  private readonly http = inject(HttpClient);
  private readonly config = inject(APP_CONFIG);

  list(filters: OrderFilters) {
    const params = new HttpParams()
      .set('page', filters.page)
      .set('status', filters.status);
    return this.http.get<Order[]>(`${this.config.apiBaseUrl}/orders`, { params });
  }

  get(id: string) {
    return this.http.get<Order>(`${this.config.apiBaseUrl}/orders/${id}`);
  }
}
```

Keep the API thin. It builds URLs and types responses; it does not hold state.

## Store

```ts
// data/order-store.ts
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
  readonly isEmpty = computed(() => !this.loading() && this.orders().length === 0);

  async load(filters: OrderFilters): Promise<void> {
    this.loadingState.set(true);
    this.errorState.set(null);
    try {
      this.ordersState.set(await firstValueFrom(this.api.list(filters)));
    } catch {
      this.errorState.set('Could not load orders. Try again.');
    } finally {
      this.loadingState.set(false);
    }
  }

  clear(): void {
    this.ordersState.set([]);
    this.errorState.set(null);
  }
}
```

The store is route-scoped, so it is listed in `providers` and disposed when the
user leaves the feature.

## Routes

```ts
// orders.routes.ts
import { Routes } from '@angular/router';
import { OrderStore } from './data/order-store';

export const ordersRoutes: Routes = [
  {
    path: '',
    providers: [OrderStore],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./feature/order-list-page').then((m) => m.OrderListPage),
        title: 'Orders',
      },
      {
        path: ':orderId',
        loadComponent: () =>
          import('./feature/order-detail-page').then((m) => m.OrderDetailPage),
        title: 'Order details',
      },
    ],
  },
];
```

## Page

```ts
// feature/order-list-page.ts
import { Component, effect, inject, input } from '@angular/core';
import { OrderStore } from '../data/order-store';
import { OrderCard } from '../ui/order-card';
import { OrderStatus } from '../data/order.model';

@Component({
  selector: 'app-order-list-page',
  imports: [OrderCard],
  templateUrl: './order-list-page.html',
})
export class OrderListPage {
  private readonly store = inject(OrderStore);

  readonly status = input<OrderStatus | 'all'>('all');
  readonly page = input(1, {
    transform: (value: string | number) => Math.max(1, Number(value) || 1),
  });

  readonly orders = this.store.orders;
  readonly loading = this.store.loading;
  readonly error = this.store.error;
  readonly isEmpty = this.store.isEmpty;

  constructor() {
    effect(() => {
      void this.store.load({ status: this.status(), page: this.page() });
    });
  }
}
```

```html
<!-- feature/order-list-page.html -->
<h1>Orders</h1>

@if (loading()) {
  <p role="status">Loading orders…</p>
} @else if (error()) {
  <p role="alert">{{ error() }}</p>
} @else if (isEmpty()) {
  <p>No orders match these filters.</p>
} @else {
  <ul>
    @for (order of orders(); track order.id) {
      <li><app-order-card [order]="order" /></li>
    }
  </ul>
}
```

`withComponentInputBinding()` maps `:orderId` and query params to inputs. The
effect reloads when an input changes; use `httpResource` instead when the data is
a pure function of those inputs and you want caching and cancellation for free.

## Presentational component

```ts
// ui/order-card.ts
import { CurrencyPipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { Order } from '../data/order.model';
import { OrderStatusBadge } from './order-status-badge';

@Component({
  selector: 'app-order-card',
  imports: [CurrencyPipe, OrderStatusBadge],
  template: `
    <article>
      <h2>{{ order().customerName }}</h2>
      <app-order-status-badge [status]="order().status" />
      <p>{{ order().totalCents / 100 | currency }}</p>
      <button type="button" (click)="selected.emit(order().id)">View</button>
    </article>
  `,
})
export class OrderCard {
  readonly order = input.required<Order>();
  readonly selected = output<string>();
}
```

No router, HTTP, or store in this component. It renders one order and emits an
intent.

## Dependency rules

```text
features/orders  →  shared, core
features/checkout →  shared, core
core             →  (nothing app-specific)
shared           →  (nothing app-specific)
```

Enforce the direction in review. If two features need the same domain code,
move the domain model or a pure service to `shared/` only when it is truly
generic; otherwise expose a narrow API from the owning feature.

# Component patterns

Copy these patterns; keep the contracts narrow.

## Signal inputs and derived state

```ts
import { Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-price',
  template: `<span>{{ formatted() }}</span>`,
})
export class Price {
  readonly amountCents = input.required<number>();
  readonly currency = input('USD');
  readonly locale = input('en-US');

  readonly formatted = computed(() =>
    new Intl.NumberFormat(this.locale(), {
      style: 'currency',
      currency: this.currency(),
    }).format(this.amountCents() / 100),
  );
}
```

`computed()` recalculates only when an input changes. Do not format in the
template.

## Two-way binding with `model()`

```ts
@Component({
  selector: 'app-search-box',
  template: `
    <input
      type="search"
      [value]="query()"
      (input)="query.set(($any($event.target)).value)"
      [attr.aria-label]="label()"
    />
  `,
})
export class SearchBox {
  readonly query = model('');
  readonly label = input('Search');
}
```

```html
<app-search-box [(query)]="searchTerm" />
```

Use `model()` only when the child is the natural owner of the edit. Otherwise
use an input plus an output and let the parent decide.

## Optional and transformed inputs

```ts
readonly page = input(1, {
  transform: (value: number | string) => Math.max(1, Number(value) || 1),
});

readonly size = input<'sm' | 'md' | 'lg'>('md');
```

- Transform at the boundary so the rest of the component sees one type.
- Keep transforms pure and cheap.
- Do not use a transform to hide a breaking API change.

## Content projection with fallback

```ts
@Component({
  selector: 'app-empty-state',
  template: `
    <div class="empty-state">
      <ng-content>
        <p>Nothing here yet.</p>
      </ng-content>
    </div>
  `,
})
export class EmptyState {}
```

Projected content replaces the fallback entirely. If you need to know whether
content was provided, use a `contentChild()` signal.

## Deferred content

```html
@defer (on viewport) {
  <app-heavy-chart [data]="data()" />
} @placeholder {
  <div class="chart-skeleton" aria-hidden="true"></div>
} @loading (minimum 200ms) {
  <app-spinner />
} @error {
  <p role="alert">The chart could not load.</p>
}
```

- Use `on viewport` for below-the-fold widgets, `on idle` for non-critical
  extras, and `on interaction` for content behind a click.
- Always provide a placeholder with the same dimensions to avoid layout shift.
- Keep deferred content out of the initial bundle.
- Do not defer above-the-fold LCP content.

## Dynamic components

```ts
import { Component, ViewContainerRef, inject, viewChild } from '@angular/core';

@Component({
  selector: 'app-widget-host',
  template: `<ng-container #host />`,
})
export class WidgetHost {
  private readonly host = viewChild.required('host', { read: ViewContainerRef });

  async showChart(): Promise<void> {
    const { ChartWidget } = await import('./chart-widget');
    this.host().createComponent(ChartWidget);
  }
}
```

Prefer route-level lazy loading or `@defer` over manual dynamic components.
Use `ViewContainerRef` only for genuinely dynamic composition.

## Host directives

```ts
@Directive({
  selector: '[appTooltip]',
  host: {
    '[attr.aria-describedby]': 'tooltipId',
    '(mouseenter)': 'show()',
    '(mouseleave)': 'hide()',
    '(focus)': 'show()',
    '(blur)': 'hide()',
  },
})
export class Tooltip {
  readonly text = input.required<string>({ alias: 'appTooltip' });
  readonly tooltipId = `tooltip-${crypto.randomUUID()}`;
  readonly visible = signal(false);

  show(): void { this.visible.set(true); }
  hide(): void { this.visible.set(false); }
}
```

```ts
@Component({
  selector: 'app-icon-button',
  hostDirectives: [{ directive: Tooltip, inputs: ['appTooltip'] }],
  template: `<ng-content />`,
})
export class IconButton {}
```

- Host directives compose behavior without inheritance.
- Expose only the inputs and outputs the host component should support.
- Do not use host directives to hide a dependency the component actually needs.

## Directive with typed host element

```ts
import {
  Directive,
  DestroyRef,
  ElementRef,
  afterNextRender,
  inject,
  input,
} from '@angular/core';

@Directive({ selector: '[appAutosize]' })
export class Autosize {
  private readonly el = inject<ElementRef<HTMLTextAreaElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  readonly minRows = input(2);

  constructor() {
    afterNextRender(() => {
      const el = this.el.nativeElement;
      const onInput = () => this.resize();
      el.addEventListener('input', onInput);
      this.destroyRef.onDestroy(() => el.removeEventListener('input', onInput));
      this.resize();
    });
  }

  private resize(): void {
    const el = this.el.nativeElement;
    el.rows = this.minRows();
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }
}
```

Register DOM listeners through the `host` object when possible so Angular owns
cleanup. For imperative listeners, remove them in `DestroyRef.onDestroy()`.

## Error boundary

```html
<section>
  @boundary {
    <app-recommendations [userId]="userId()" />
  }
  @error (let error) {
    <app-recommendations-fallback />
  }
  <app-cart-summary />
</section>
```

`@boundary` is a developer preview in v22. Confirm the flag and stability in the
installed version. Do not wrap the whole app in one boundary; isolate widgets
that can fail independently.

## Testable component skeleton

```ts
import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-user-badge',
  template: `
    <span [class.inactive]="!active()">{{ name() }}</span>
    <button type="button" (click)="removed.emit()" [attr.aria-label]="'Remove ' + name()">
      ×
    </button>
  `,
})
export class UserBadge {
  readonly name = input.required<string>();
  readonly active = input(true);
  readonly removed = output<void>();
}
```

```ts
it('emits when remove is clicked', async () => {
  const fixture = TestBed.createComponent(UserBadge);
  fixture.componentRef.setInput('name', 'Ada');
  await fixture.whenStable();

  const removed = vi.fn();
  fixture.componentInstance.removed.subscribe(removed);

  fixture.nativeElement.querySelector('button').click();

  expect(removed).toHaveBeenCalledOnce();
});
```

Inputs and outputs are the whole contract, so no HTTP or router setup is needed.

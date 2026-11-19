---
name: Angular Components
description: Build modern Angular components with signal inputs and outputs, model inputs, host bindings, content projection, built-in control flow, deferrable views, and clean lifecycle handling. Use when writing or reviewing a component, template, directive, or component API.
---

# Angular Components

A component is a small contract: inputs in, outputs out, a template that renders
state. Keep that contract narrow and the component stays easy to test, reuse, and
delete.

## Component API

Use signal-based APIs for new code. They are typed, reactive, and work with
zoneless change detection.

```ts
import { Component, input, output, model, computed } from '@angular/core';

@Component({
  selector: 'app-quantity-picker',
  template: `
    <button type="button" (click)="decrement()" [disabled]="value() <= min()">−</button>
    <input
      type="number"
      [value]="value()"
      [min]="min()"
      [max]="max()"
      (input)="onInput($event)"
      [attr.aria-label]="label()"
    />
    <button type="button" (click)="increment()" [disabled]="value() >= max()">+</button>
  `,
})
export class QuantityPicker {
  readonly value = model.required<number>();
  readonly min = input(1);
  readonly max = input(99);
  readonly label = input('Quantity');
  readonly changed = output<number>();

  readonly canDecrement = computed(() => this.value() > this.min());

  increment(): void {
    const next = Math.min(this.value() + 1, this.max());
    this.value.set(next);
    this.changed.emit(next);
  }

  decrement(): void {
    const next = Math.max(this.value() - 1, this.min());
    this.value.set(next);
    this.changed.emit(next);
  }

  onInput(event: Event): void {
    const next = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(next)) {
      this.value.set(Math.min(Math.max(next, this.min()), this.max()));
    }
  }
}
```

| API | Use for |
| --- | --- |
| `input()` | One-way data in |
| `input.required()` | Data the component cannot render without |
| `output()` | Events out |
| `model()` | Two-way binding (`[(value)]`) |
| `computed()` | Derived state from inputs/signals |
| `viewChild()` / `contentChild()` | Template or content references |

- Do not mutate an `input()`. It is read-only. Derive with `computed()` or use
  `model()` when the child must write back.
- Do not expose a public writable signal. Return `asReadonly()` or a computed.
- Name outputs for events, not commands: `selected`, `closed`, `valueChanged`.
- Avoid `EventEmitter` in new code; `output()` is the modern API.
- Do not use `@Input()`/`@Output()` decorators in new components. Mixing styles
  in one component is confusing.

## Templates

Use built-in control flow. It is faster and type-narrowing works better than
`*ngIf`/`*ngFor`.

```html
@if (user(); as user) {
  <h1>Welcome, {{ user.name }}</h1>
} @else {
  <a routerLink="/login">Sign in</a>
}

@for (order of orders(); track order.id) {
  <app-order-card [order]="order" />
} @empty {
  <p>No orders yet.</p>
}

@switch (status()) {
  @case ('loading') { <app-spinner /> }
  @case ('error') { <app-error-panel /> }
  @default { <app-order-table [orders]="orders()" /> }
}
```

- `track` is required on `@for`. Track a stable identity (`id`), not `$index`,
  unless the list is static.
- Use `@empty` instead of a separate `length === 0` branch.
- Keep expressions cheap. Compute in the class, not in the template.
- Arrow functions are allowed in templates in v22, but keep them trivial. A
  template is not the place for business logic.
- Do not call methods that allocate arrays or objects on every change detection
  cycle. Use `computed()`.
- Use `@defer` for below-the-fold or heavy content. See the performance skill.

## Host bindings and host elements

```ts
@Component({
  selector: 'app-card',
  host: {
    class: 'card',
    '[class.card--selected]': 'selected()',
    '[attr.aria-busy]': 'loading()',
    '(keydown.escape)': 'closed.emit()',
  },
  template: `<ng-content />`,
})
export class Card {
  readonly selected = input(false);
  readonly loading = input(false);
  readonly closed = output<void>();
}
```

- Prefer the `host` object over `@HostBinding`/`@HostListener`.
- Bind classes and attributes on the host, not on an extra wrapper `div`.
- Do not read `ElementRef.nativeElement` to change styles. Use bindings.
- If you need direct DOM access, use `viewChild` with a typed element reference
  and `afterNextRender`, and explain why.

## Content projection

```ts
@Component({
  selector: 'app-panel',
  template: `
    <header><ng-content select="[panel-title]" /></header>
    <section><ng-content /></section>
    <footer><ng-content select="[panel-actions]" /></footer>
  `,
})
export class Panel {}
```

```html
<app-panel>
  <h2 panel-title>Billing</h2>
  <p>Update your payment method.</p>
  <button panel-actions type="button">Save</button>
</app-panel>
```

- Use `ng-content` for static projection and `ng-template` plus
  `contentChild()` when the parent needs to control when content renders.
- Do not query projected content in the constructor; it is not available yet.
- Avoid `@ContentChild` with `static: true` unless you truly need it before
  change detection.
- Keep slot names stable; they are part of the component API.

## Lifecycle and effects

- Prefer signals and `computed()` over lifecycle hooks for derived state.
- Use `effect()` only for side effects that must react to signal changes:
  logging, storage, imperative DOM, analytics. Do not use it to copy one signal
  into another.
- Use `afterNextRender()` / `afterRenderEffect()` for DOM measurement and
  third-party widget initialization.
- Use `DestroyRef` or `takeUntilDestroyed()` for cleanup. Do not rely on manual
  `ngOnDestroy` for every subscription.
- `ngOnInit` is still fine for non-signal setup, but it is not a place to fetch
  data if a `resource` or route resolver expresses it better.
- Never fetch data in a constructor without handling errors and cancellation.

## Change detection

Angular 22 makes OnPush the default for new applications and zoneless the
default since v21.

- Write components that are correct under OnPush: update via signals or
  observables that Angular tracks, not by mutating objects in place.
- Do not inject `ChangeDetectorRef` to paper over a missing signal. Fix the data
  flow.
- Do not assume Zone.js patches timers, promises, or XHR. In a zoneless app they
  do not trigger change detection.
- If a third-party callback mutates state outside Angular, update a signal from
  it. The signal notifies the scheduler.
- Avoid `setTimeout` for rendering coordination. Use `afterNextRender`.

## Styling

- Use component styles with the default emulated encapsulation.
- Style the host with `:host`; expose sizing and layout through inputs or CSS
  custom properties.
- Use design tokens (`--color-surface`, `--space-3`) instead of hard-coded
  values.
- Avoid `::ng-deep`. If a child must be styled, expose a documented custom
  property or a variant input.
- Keep global styles for reset, tokens, typography, and layout primitives only.
- Do not select elements by tag in global CSS; it makes components fragile.

## Accessibility baseline

- Use real elements: `button`, `a`, `input`, `label`, `dialog`. A clickable `div`
  is a bug.
- Every input has a label. Every image has an `alt` (empty for decorative).
- Do not remove focus outlines without a visible replacement.
- Announce async status with `role="status"` and errors with `role="alert"`.
- See the `angular-accessibility` skill for patterns and testing.

## Testing seam

- Keep presentational components free of HTTP and routing so they can be tested
  with `TestBed` and inputs only.
- Use `fixture.componentRef.setInput()` to set signal inputs.
- Assert what the user sees, not private fields. See `angular-testing`.

## Anti-patterns

- `@Input()`/`@Output()` decorators in new code alongside signal APIs.
- Mutating an input object or array in place.
- A public `signal` that any consumer can overwrite.
- Business logic or HTTP calls inside a presentational component.
- `*ngIf`/`*ngFor` in a new template.
- `track $index` for a reorderable list.
- Method calls in templates that allocate or sort.
- `ChangeDetectorRef.detectChanges()` as a default fix.
- `ElementRef.nativeElement.innerHTML` without sanitization.
- `::ng-deep` reaching into a child component.
- Clickable `div`s, unlabeled inputs, or removed focus rings.
- A component with 15 inputs and no view model.
- `effect()` used to synchronize two writable signals.

## Checklist

- [ ] Signal inputs/outputs/model are used; no decorator inputs in new code.
- [ ] Inputs are not mutated; derived state uses `computed()`.
- [ ] Public state is read-only.
- [ ] Template uses `@if`/`@for`/`@switch` and a stable `track`.
- [ ] No expensive calls or allocations in the template.
- [ ] Host bindings use the `host` object.
- [ ] Content projection has a documented, stable API.
- [ ] Effects are limited to real side effects and cleaned up.
- [ ] Component is correct under OnPush and zoneless change detection.
- [ ] Styles use encapsulation and design tokens; no `::ng-deep`.
- [ ] Semantics, labels, focus, and live regions are correct.
- [ ] The component can be tested with inputs and outputs alone.

## References

- `references/component-patterns.md` — inputs, two-way binding, projection,
  deferred content, dynamic components, and host directives.

# Forms recipes

## Complete Signal Form with server errors

```ts
import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import {
  email,
  form,
  FormField,
  minLength,
  required,
  submit,
} from '@angular/forms/signals';
import { OrderApi } from '../data/order-api';

interface CheckoutModel {
  customerName: string;
  email: string;
  notes: string;
}

@Component({
  selector: 'app-checkout-form',
  imports: [FormField],
  templateUrl: './checkout-form.html',
})
export class CheckoutForm {
  private readonly api = inject(OrderApi);
  private readonly router = inject(Router);
  private readonly idempotencyKey = crypto.randomUUID();

  readonly model = signal<CheckoutModel>({
    customerName: '',
    email: '',
    notes: '',
  });

  readonly serverError = signal<string | null>(null);
  readonly submitting = signal(false);

  readonly checkoutForm = form(this.model, (path) => {
    required(path.customerName, { message: 'Name is required' });
    minLength(path.customerName, 2, { message: 'Use at least 2 characters' });
    required(path.email, { message: 'Email is required' });
    email(path.email, { message: 'Enter a valid email address' });
  });

  async onSubmit(event: Event): Promise<void> {
    event.preventDefault();
    this.serverError.set(null);
    this.submitting.set(true);

    try {
      await submit(this.checkoutForm, {
        action: async () => {
          await this.api.create(this.model(), { idempotencyKey: this.idempotencyKey });
          await this.router.navigate(['/orders']);
        },
      });
    } catch (error) {
      this.serverError.set('We could not place your order. Please try again.');
    } finally {
      this.submitting.set(false);
    }
  }
}
```

```html
<form (submit)="onSubmit($event)" novalidate>
  @if (serverError()) {
    <p role="alert">{{ serverError() }}</p>
  }

  <label>
    Name
    <input [formField]="checkoutForm.customerName" autocomplete="name" />
  </label>
  @if (checkoutForm.customerName().touched() && checkoutForm.customerName().invalid()) {
    <p role="alert">{{ checkoutForm.customerName().errors()[0]?.message }}</p>
  }

  <label>
    Email
    <input type="email" [formField]="checkoutForm.email" autocomplete="email" />
  </label>
  @if (checkoutForm.email().touched() && checkoutForm.email().invalid()) {
    <p role="alert">{{ checkoutForm.email().errors()[0]?.message }}</p>
  }

  <label>
    Notes
    <textarea [formField]="checkoutForm.notes"></textarea>
  </label>

  <button
    type="submit"
    [disabled]="checkoutForm().invalid() || checkoutForm().pending() || submitting()"
  >
    {{ submitting() ? 'Placing order…' : 'Place order' }}
  </button>
</form>
```

## Cross-field validation

```ts
import { form, required, validate } from '@angular/forms/signals';

readonly passwordForm = form(this.passwords, (path) => {
  required(path.password, { message: 'Password is required' });
  required(path.confirm, { message: 'Confirm your password' });

  validate(path.confirm, ({ value, valueOf }) => {
    if (value() !== valueOf(path.password)) {
      return { kind: 'mismatch', message: 'Passwords do not match' };
    }
    return undefined;
  });
});
```

## Conditional fields

```ts
import { applyWhen, required } from '@angular/forms/signals';

readonly shippingForm = form(this.shipping, (path) => {
  applyWhen(
    path.shipsInternationally,
    ({ value }) => value(),
    (international) => {
      required(international.country, { message: 'Country is required' });
      required(international.postalCode, { message: 'Postal code is required' });
    },
  );
});
```

`applyWhen` takes a path, a predicate, and a schema callback. Do not call paths
inside the predicate; use the context's `valueOf`/`value`.

## Async username check

```ts
import { validateHttp } from '@angular/forms/signals';

readonly signupForm = form(this.signup, (path) => {
  required(path.username, { message: 'Username is required' });

  validateHttp(path.username, {
    request: ({ value }) => `/api/usernames/${encodeURIComponent(value())}`,
    onSuccess: (result: { available: boolean }) =>
      result.available ? undefined : { kind: 'taken', message: 'Username is taken' },
    onError: () => ({
      kind: 'unavailable',
      message: 'Could not check availability. Try again.',
    }),
  });
});
```

```html
@if (signupForm.username().pending()) {
  <p role="status">Checking availability…</p>
}
```

## Dynamic array with stable rows

```ts
import { applyEach, form, FormField, min, required } from '@angular/forms/signals';

interface Line {
  id: string;
  sku: string;
  quantity: number;
}

readonly model = signal({
  lines: [{ id: crypto.randomUUID(), sku: '', quantity: 1 }] as Line[],
});

readonly lineForm = form(this.model, (path) => {
  applyEach(path.lines, (line) => {
    required(line.sku, { message: 'SKU is required' });
    min(line.quantity, 1, { message: 'Quantity must be at least 1' });
  });
});

addLine(): void {
  this.model.update((model) => ({
    ...model,
    lines: [...model.lines, { id: crypto.randomUUID(), sku: '', quantity: 1 }],
  }));
}

removeLine(id: string): void {
  this.model.update((model) => ({
    ...model,
    lines: model.lines.filter((line) => line.id !== id),
  }));
}
```

```html
@for (line of lineForm.lines; track line.id) {
  <fieldset>
    <legend>Line item</legend>
    <input [formField]="line.sku" aria-label="SKU" />
    <input type="number" [formField]="line.quantity" aria-label="Quantity" />
    <button type="button" (click)="removeLine(line.id)">Remove</button>
  </fieldset>
}
```

## Server field errors

When the API returns a field-keyed error object, map it to a form-level message
or a custom validator. Keep the mapping in one adapter:

```ts
interface ApiValidationError {
  field: string;
  message: string;
}

function applyServerErrors(
  errors: ApiValidationError[],
  setFormError: (message: string) => void,
): void {
  const first = errors[0];
  if (first) setFormError(first.message);
}
```

For field-level mapping, store the server errors in a signal and render them
next to the matching control. Do not stuff server messages into client
validators; they are not derived from the current value.

## Reactive forms: typed group and cleanup

```ts
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, Validators } from '@angular/forms';

@Component({ /* ... */ })
export class LegacyProfileForm {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly form = this.fb.group({
    displayName: ['', [Validators.required, Validators.minLength(2)]],
    website: [''],
  });

  constructor() {
    this.form.controls.website.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((website) => this.preview.set(website));
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.save(this.form.getRawValue());
  }
}
```

## Migrating reactive forms to Signal Forms

1. Convert the model to a `signal<T>` with non-null defaults.
2. Replace `FormGroup`/`FormControl` with `form(model, schema)`.
3. Move `Validators.*` into schema rules.
4. Replace `[formControlName]` with `[formField]`.
5. Replace `valueChanges` subscriptions with `computed` or effects only for
   genuine side effects.
6. Keep the same server contract and tests; migrate one form at a time.

Do not migrate a form that has no tests and no active work. The risk is higher
than the benefit.

---
name: Angular Forms
description: Build production Angular forms with Signal Forms, schema validation, async validators, dynamic arrays, server error mapping, accessible error display, and idempotent submission. Use when creating a form, migrating from reactive forms, or reviewing validation and submission behavior.
---

# Angular Forms

A form is a contract with the user and the server. Validate at the boundary,
show errors where they can be fixed, and make submission safe to retry.

## Choose the API

| Situation | Use |
| --- | --- |
| New form on Angular 22+ | Signal Forms |
| Existing reactive forms | Keep them; migrate incrementally |
| Complex custom controls not yet signal-aware | Reactive Forms, isolated behind an adapter |
| One or two simple fields | Signal Forms or a local signal with explicit validation |

Signal Forms are stable in Angular 22. Do not rewrite a working reactive form
just to follow fashion; migrate when you touch the form and the team can test it.

## Signal Forms basics

```ts
import { Component, signal } from '@angular/core';
import { email, form, FormField, required, submit } from '@angular/forms/signals';

interface LoginModel {
  email: string;
  password: string;
}

@Component({
  selector: 'app-login',
  imports: [FormField],
  templateUrl: './login.html',
})
export class Login {
  readonly model = signal<LoginModel>({ email: '', password: '' });

  readonly loginForm = form(this.model, (path) => {
    required(path.email, { message: 'Email is required' });
    email(path.email, { message: 'Enter a valid email address' });
    required(path.password, { message: 'Password is required' });
  });

  onSubmit(event: Event): void {
    event.preventDefault();
    submit(this.loginForm, {
      action: async () => {
        await this.auth.login(this.model());
      },
    });
  }
}
```

```html
<form (submit)="onSubmit($event)">
  <label>
    Email
    <input type="email" [formField]="loginForm.email" />
  </label>
  @if (loginForm.email().touched() && loginForm.email().invalid()) {
    <ul role="alert">
      @for (error of loginForm.email().errors(); track error.kind) {
        <li>{{ error.message }}</li>
      }
    </ul>
  }

  <button type="submit" [disabled]="loginForm().invalid() || loginForm().pending()">
    Sign in
  </button>
</form>
```

Key rules:

- The form structure is derived from the model. Start every field with a
  non-null value (`''`, `0`, `[]`, `false`).
- The schema callback receives paths. Paths are not signals and are not
  callable.
- To read state in a template or class, call the field first:
  `loginForm.email().touched()`, `loginForm().invalid()`.
- Bind with `[formField]`. Do not also bind `value`, `min`, `max`, `disabled`,
  or `readonly`; the directive owns them.
- Update values by updating the model signal, not by setting the field.
- `submit()` marks fields touched and runs the async action only when valid.

## Validation

```ts
import {
  applyEach,
  maxLength,
  minLength,
  pattern,
  required,
  validate,
} from '@angular/forms/signals';

readonly profileForm = form(this.profile, (path) => {
  required(path.displayName, { message: 'Display name is required' });
  minLength(path.displayName, 2, { message: 'Use at least 2 characters' });
  maxLength(path.bio, 500, { message: 'Keep the bio under 500 characters' });

  required(path.website, {
    when: ({ valueOf }) => valueOf(path.publicProfile),
    message: 'A website is required for a public profile',
  });
  pattern(path.postalCode, /^\d{5}$/, { message: 'Enter a 5-digit postal code' });

  validate(path.confirmPassword, ({ value, valueOf }) => {
    if (value() !== valueOf(path.password)) {
      return { kind: 'passwordMismatch', message: 'Passwords do not match' };
    }
    return undefined;
  });

  applyEach(path.contacts, (contact) => {
    required(contact.name, { message: 'Contact name is required' });
    required(contact.email, { message: 'Contact email is required' });
  });
});
```

- Built-ins cover `required`, `email`, `min`, `max`, `minLength`, `maxLength`,
  `pattern`, `minDate`, and `maxDate`.
- Return an error object with a stable `kind` and a user-facing `message`;
  return `undefined` when valid.
- Use `when` for conditional rules, `applyWhen` for a group of rules, and
  `applyEach` for array items.
- Validation does not short-circuit; one field can show several errors.
- Show errors after `touched()` or after a submit attempt, not while the user is
  still typing the first character.
- Do not rely on native `:valid`/`:invalid` styling. Bind classes to field state.

## Async validation

```ts
import { validateHttp } from '@angular/forms/signals';

readonly signupForm = form(this.signup, (path) => {
  required(path.username, { message: 'Username is required' });
  validateHttp(path.username, {
    request: ({ value }) => `/api/usernames/${encodeURIComponent(value())}`,
    onSuccess: (result: { available: boolean }) =>
      result.available ? undefined : { kind: 'taken', message: 'That username is taken' },
    onError: () => ({ kind: 'unavailable', message: 'Could not check availability' }),
  });
});
```

- Async validation runs after synchronous validation passes.
- Show `path.username().pending()` while it runs.
- Debounce expensive checks and cancel stale requests. `validateHttp` handles
  cancellation for you; a custom `validateAsync` must use `resource` with
  `params`.
- Never block typing on a network call. Let the user continue and surface the
  result when it arrives.
- Server-side validation remains authoritative. Async client checks are UX.

## Dynamic arrays

```ts
readonly model = signal({
  items: [] as Array<{ sku: string; quantity: number }>,
});

readonly orderForm = form(this.model, (path) => {
  applyEach(path.items, (item) => {
    required(item.sku, { message: 'SKU is required' });
    min(item.quantity, 1, { message: 'Quantity must be at least 1' });
  });
});

addItem(): void {
  this.model.update((model) => ({
    ...model,
    items: [...model.items, { sku: '', quantity: 1 }],
  }));
}

removeItem(index: number): void {
  this.model.update((model) => ({
    ...model,
    items: model.items.filter((_, i) => i !== index),
  }));
}
```

```html
@for (item of orderForm.items; track $index; let i = $index) {
  <input [formField]="item.sku" aria-label="SKU" />
  <input type="number" [formField]="item.quantity" aria-label="Quantity" />
  <button type="button" (click)="removeItem(i)">Remove</button>
}
```

Use a stable identity for `track` when rows can reorder. `$index` is acceptable
only for append/remove at the end.

## Submission

```ts
async onSubmit(event: Event): Promise<void> {
  event.preventDefault();
  await submit(this.orderForm, {
    action: async () => {
      try {
        await this.orders.create(this.model(), {
          idempotencyKey: this.submissionKey,
        });
        this.router.navigate(['/orders']);
      } catch (error) {
        this.serverError.set(this.toUserMessage(error));
      }
    },
  });
}
```

- Disable submit while `invalid()` or `pending()`, and explain why if it is not
  obvious.
- Generate one idempotency key per form session; reuse it on retry.
- Map server field errors back onto the form. Keep a form-level error for
  anything that is not field-specific.
- Do not clear the form until the server confirms success.
- Prevent double submission with a pending flag in addition to the disabled
  attribute.
- On success, navigate or show a confirmation; do not leave a stale form.
- Preserve drafts for long forms when the product needs it.

## Reactive forms fallback

If the project already uses reactive forms, keep them typed and consistent:

```ts
import { NonNullableFormBuilder, Validators } from '@angular/forms';

private readonly fb = inject(NonNullableFormBuilder);

readonly form = this.fb.group({
  email: ['', [Validators.required, Validators.email]],
  password: ['', [Validators.required, Validators.minLength(12)]],
});

submit(): void {
  if (this.form.invalid) {
    this.form.markAllAsTouched();
    return;
  }
  this.auth.login(this.form.getRawValue());
}
```

- Use `NonNullableFormBuilder` so controls are not `null`.
- Type the form value; do not cast to `any`.
- Mark all as touched on submit so errors become visible.
- Clean up value-change subscriptions with `takeUntilDestroyed`.
- Do not mix reactive forms and signal forms in the same form.

## Accessibility

- Every control has a visible `<label>` or an accessible name.
- Link errors with `aria-describedby` and set `aria-invalid="true"`.
- Use `role="alert"` for a submit-level error and a live region for async
  status.
- Move focus to the first invalid field or an error summary after a failed
  submit.
- Do not rely on color alone to indicate errors.
- Group related controls with `fieldset` and `legend`.
- See `angular-accessibility` for the full checklist.

## Anti-patterns

- Nullable initial values in a Signal Forms model.
- Binding `[value]`, `[disabled]`, `min`, or `max` alongside `[formField]`.
- Calling a field path without calling it (`form.email.valid()`).
- Using `effect()` to copy form values into another signal.
- Validating only on the client and trusting the result on the server.
- Disabling submit with no explanation.
- Showing every error on page load.
- Losing user input on a failed request.
- Retrying a create without an idempotency key.
- One giant form component with no field-level components.
- Mixing reactive forms and Signal Forms in one feature.

## Checklist

- [ ] Form API choice is explicit and consistent within the feature.
- [ ] Model has non-null initial values and precise types.
- [ ] Schema validation covers required, format, range, and cross-field rules.
- [ ] Async validation is debounced, cancellable, and non-blocking.
- [ ] Array fields use `applyEach` and stable tracking.
- [ ] Errors appear after touch or submit, not on first render.
- [ ] Server field errors map back to the form.
- [ ] Submission is idempotent and cannot double-fire.
- [ ] Form state survives a failed request.
- [ ] Labels, error associations, focus, and live regions are correct.
- [ ] Tests cover invalid, pending, server-error, and success paths.

## References

- `references/forms-recipes.md` — complete Signal Forms, async validation,
  server errors, dynamic arrays, and reactive-form migration notes.

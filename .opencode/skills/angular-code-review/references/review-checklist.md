# Angular code review checklist

Copy the relevant sections into a pull request review. Delete what does not
apply; do not approve by checklist alone.

## Summary

```text
Verdict: approve / request changes / comment
Blocking: <n>
Major: <n>
Minor: <n>
Risk: low / medium / high
Rollback: <how>
```

## Correctness

- [ ] The change does what the description says.
- [ ] Empty, loading, error, and success states are handled.
- [ ] Async work is cancelled on input change or destroy.
- [ ] Overlapping requests cannot corrupt state.
- [ ] Dates, timezones, money, and rounding are correct.
- [ ] Mutations are idempotent or protected by an idempotency key.
- [ ] The feature works with the flag off and on a cold cache.
- [ ] The change works on a slow network and a small viewport.

## Security

- [ ] No untrusted value reaches `innerHTML`, `bypassSecurityTrust*`, `eval`, or
      `new Function`.
- [ ] Redirect targets are validated; no open redirect.
- [ ] Tokens are not in URLs, logs, analytics, or error reports.
- [ ] The server enforces authorization; guards are UX only.
- [ ] `postMessage` validates `event.origin` and message shape.
- [ ] SSR does not leak secrets or share request state.
- [ ] New dependencies are reviewed for maintenance, license, and bundle cost.
- [ ] Credentials are sent only to trusted origins.

## State

- [ ] Each piece of state has one owner.
- [ ] Derived state uses `computed()`, not an effect or duplicate signal.
- [ ] Server data has an invalidation rule.
- [ ] Subscriptions use `takeUntilDestroyed` or `DestroyRef`.
- [ ] `effect()` is used only for side effects.
- [ ] URL-backed filters, sort, and paging remain in the URL.
- [ ] Feature stores are route-scoped when appropriate.
- [ ] Optimistic updates roll back on failure.

## Components

- [ ] Signal inputs/outputs/model are used; no decorator inputs in new code.
- [ ] Inputs are not mutated; public state is read-only.
- [ ] `@if`/`@for`/`@switch` are used; `track` is stable.
- [ ] No expensive calls or allocations in templates.
- [ ] Host bindings use the `host` object.
- [ ] Effects are limited and cleaned up.
- [ ] The component is correct under OnPush and zoneless.
- [ ] No `ChangeDetectorRef.detectChanges()` papering over a bug.
- [ ] Presentational components do not inject HTTP or Router.
- [ ] Component has one reason to change.

## Forms

- [ ] One form API per form; Signal Forms and reactive forms are not mixed.
- [ ] Model has non-null defaults and precise types.
- [ ] Required, format, range, and cross-field rules are covered.
- [ ] Async validation is debounced, cancellable, and non-blocking.
- [ ] Errors appear after touch or submit.
- [ ] Server field errors map back to the form.
- [ ] Submission cannot double-fire and is safe to retry.
- [ ] User input survives a failed request.
- [ ] Labels and error associations are present.

## Performance

- [ ] New features are lazy-loaded.
- [ ] No heavy dependency entered the initial bundle.
- [ ] Images have dimensions and responsive sources; only LCP uses `priority`.
- [ ] Below-the-fold widgets are deferred.
- [ ] Long lists are tracked and virtualized if needed.
- [ ] Bundle budgets were not raised without justification.
- [ ] No new long tasks, polling, or scroll listeners.
- [ ] SSR output matches the client.

## Accessibility

- [ ] Semantic elements are used; no clickable `div`.
- [ ] Controls have labels and accessible names.
- [ ] Keyboard operation and focus order are correct.
- [ ] Dialogs trap and restore focus.
- [ ] Route changes update title and announce.
- [ ] Errors and status use the right live region.
- [ ] Color is not the only signal; contrast holds.
- [ ] axe or manual checks cover the new UI.

## Tests

- [ ] A test would fail without the change.
- [ ] Tests assert behavior, not internals.
- [ ] Async tests await stability; no sleeps.
- [ ] Error and unauthorized paths are covered.
- [ ] HTTP is mocked; no real network.
- [ ] Tests are deterministic and isolated.
- [ ] Coverage did not drop in a meaningful area.

## Hygiene

- [ ] PR description covers problem, approach, risk, and rollback.
- [ ] UI changes include screenshots or recordings.
- [ ] Behavior changes are separate from mechanical changes.
- [ ] No debug logs, commented-out code, or temporary flags.
- [ ] No unrelated formatting churn.
- [ ] New env vars and secrets are documented.
- [ ] Migrations and feature flags have a rollback path.

## Comment template

```text
**Blocking — <area>**
<file>:<line>
<What is wrong and why it matters.>
Suggested fix: <concrete change or code sketch.>
```

```text
**Consider — <area>**
<Optional improvement and the trade-off.>
```

Use "Blocking" only for data loss, security, crashes, or broken core flows. Use
"Major" for real-scenario bugs, leaks, and accessibility failures.

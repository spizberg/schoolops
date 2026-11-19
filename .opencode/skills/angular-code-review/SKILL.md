---
name: Angular Code Review
description: Review Angular changes for correctness, state ownership, component contracts, forms, security, performance, accessibility, and tests, and report findings by severity. Use when reviewing a pull request or before merging Angular code.
---

# Angular Code Review

Review for the failure the user will experience, not for style preferences. A
review that only renames variables misses the bugs that matter.

## Review order

1. **Correctness** — Does it do what the change says? Are edge cases handled?
2. **Security** — Untrusted input, auth, secrets, unsafe DOM, redirects.
3. **State and data flow** — One owner, no stale copies, cancellation, errors.
4. **Component contract** — Inputs, outputs, mutation, lifecycle, OnPush.
5. **Forms** — Validation, submission, server errors, idempotency.
6. **Performance** — Bundle, change detection, lazy loading, lists, images.
7. **Accessibility** — Semantics, keyboard, focus, labels, announcements.
8. **Tests** — Behavior covered, deterministic, meaningful assertions.
9. **Maintainability** — Naming, boundaries, duplication, dead code.

Style and formatting belong to the formatter and linter. Do not spend review
comments on what tooling enforces.

## Severity

| Level | Meaning | Action |
| --- | --- | --- |
| Blocking | Data loss, security hole, crash, broken core flow | Must fix before merge |
| Major | Wrong behavior in a real scenario, leak, a11y failure | Should fix before merge |
| Minor | Maintainability, clarity, small edge case | Fix now or file a follow-up |
| Nit | Preference not covered by tooling | Optional; do not block |

State the level explicitly. "This is blocking because…" is more useful than a
vague request.

## Correctness

- Does the change handle empty, loading, error, and success states?
- Are async operations cancelled when inputs change or the component is
  destroyed?
- Are errors surfaced to the user and reported to telemetry?
- Are race conditions possible with overlapping requests?
- Are numeric, date, timezone, and currency boundaries correct?
- Is a mutation retried safely, and is it idempotent?
- Does the change work on a slow network and a cold cache?
- Is feature-flagged code safe when the flag is off?

## Security

- Is any untrusted value passed to `innerHTML`, `bypassSecurityTrust*`, `eval`,
  or `new Function`?
- Are redirect targets validated against an allowlist?
- Are tokens kept out of URLs, logs, and analytics?
- Is authorization enforced by the server, not only by a guard?
- Is `postMessage` checking `event.origin`?
- Does SSR leak secrets or share request state?
- Was a dependency added without review?
- Are new endpoints sending credentials to the right origin?

## State

- Is there one owner for each piece of state?
- Is derived state computed rather than synchronized with an effect?
- Is server data copied into a writable signal with no invalidation rule?
- Are subscriptions cleaned up with `takeUntilDestroyed` or `DestroyRef`?
- Is `effect()` used for a real side effect, not state derivation?
- Are URL-backed filters still in the URL?
- Is the store scoped to the route when it should be?
- Does a failed optimistic update roll back?

## Components

- Signal inputs/outputs/model used consistently; no decorator inputs in new code.
- Inputs are not mutated; public state is read-only.
- Templates use `@if`/`@for`/`@switch` with a stable `track`.
- No expensive calls or allocations in the template.
- Host bindings use the `host` object.
- Effects are limited and cleaned up.
- Component is correct under OnPush and zoneless change detection.
- No `ChangeDetectorRef.detectChanges()` used to hide a data-flow bug.
- Content projection and host directives have a narrow, documented API.
- Component has one reason to change; no HTTP or routing in presentational code.

## Forms

- Signal Forms or reactive forms chosen consistently; not mixed in one form.
- Model has non-null defaults and precise types.
- Validation covers required, format, range, and cross-field rules.
- Async validation is debounced, cancellable, and non-blocking.
- Errors appear after touch/submit, not on first render.
- Server field errors map back to the form.
- Submission is idempotent and cannot double-fire.
- User input survives a failed request.
- Labels, `aria-invalid`, and `aria-describedby` are wired.

## Performance

- Is the new feature route lazy-loaded?
- Does it pull a heavy dependency into the initial bundle?
- Are images dimensioned, responsive, and lazy except for LCP?
- Are below-the-fold widgets deferred?
- Are long lists tracked and virtualized?
- Did the bundle budget change? If it was raised, why?
- Are there new long tasks, timers, or scroll listeners?
- Does SSR still render the same output as the client?

## Accessibility

- Semantic elements are used; no clickable `div`.
- Every control has a label and an accessible name.
- Keyboard operation, focus order, and focus visibility are correct.
- Dialogs trap and restore focus.
- Route changes update the title and announce.
- Errors and status changes use the right live region.
- Color is not the only signal; contrast holds.
- axe or manual checks cover the new UI.

## Tests

- Does the change include a test that would fail without it?
- Are tests behavior-focused rather than implementation-focused?
- Are async tests awaiting stability instead of sleeping?
- Are error and unauthorized paths covered?
- Is HTTP mocked with `HttpTestingController` rather than the real network?
- Is the test deterministic and isolated?
- Did coverage drop in a meaningful area?

## Pull request hygiene

- The description explains the problem, the approach, and the risk.
- Screenshots or recordings are attached for UI changes.
- The diff is reviewable; large mechanical changes are separated from behavior
  changes.
- Migrations, feature flags, and rollback steps are documented.
- No commented-out code, debug logs, or temporary `console.log`.
- No unrelated formatting churn.
- New environment variables and secrets are documented and provisioned.

## How to write the review

- Lead with a short summary: what works, what must change.
- Put blocking findings first, each with a file, line, and concrete fix.
- Explain the impact, not just the rule: "This leaks the token to analytics"
  beats "don't log tokens".
- Ask a question when intent is unclear; do not assume the worst.
- Distinguish "must fix" from "consider".
- Praise a good boundary or test when you see it; it reinforces the standard.
- Re-review the diff after fixes; do not approve on trust.

## Angular red flags

- `subscribe()` without cleanup.
- `effect()` copying signals.
- `any` in a service or template boundary.
- `bypassSecurityTrust*` on API or user content.
- `innerHTML` or `document.querySelector` in a component.
- `track $index` on a reorderable list.
- Eager import of a heavy feature in `app.routes.ts`.
- `providedIn: 'root'` store holding route data.
- Guard-only authorization.
- Secret in `environment.ts`.
- Missing loading/error/empty state.
- `ChangeDetectorRef.detectChanges()` as a fix.
- Tests that mock the feature under test.
- A new dependency with no bundle or maintenance review.

## Checklist

- [ ] Blocking and major findings are stated first with concrete fixes.
- [ ] Security-sensitive changes were reviewed for XSS, auth, and secrets.
- [ ] State ownership and cleanup are correct.
- [ ] Component contracts are narrow and immutable.
- [ ] Forms handle validation, server errors, and idempotency.
- [ ] Bundle and runtime performance did not regress.
- [ ] Accessibility acceptance criteria are met.
- [ ] Tests would fail without the change and cover failure paths.
- [ ] PR description covers risk, flags, and rollback.
- [ ] No debug code or unrelated churn remains.

## References

- `references/review-checklist.md` — a compact checklist to paste into a PR
  review.

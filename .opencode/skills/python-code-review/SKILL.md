---
name: Python Code Review
description: Review Python changes for correctness, security, tests, design, typing, and performance, and report findings by severity. Use when reviewing a diff, pull request, or before merging Python code.
---

# Python Code Review

A review is a risk assessment, not a style preference session. Find the defects
that tests and tooling will not catch, and keep feedback actionable.

## Order of review

1. **Understand the change.** Read the description, linked issue, and tests
   first. What problem does it solve? What is out of scope?
2. **Correctness.** Does it do what it claims for normal, boundary, and invalid
   inputs? Are there off-by-one, `None`, empty, unicode, time, or concurrency
   cases?
3. **Security.** Untrusted input, authz, injection, secrets, file paths,
   dependency changes. Load the Python Security skill for anything sensitive.
4. **Tests.** Would the tests fail if the behavior regressed? Are the important
   cases covered? Are they deterministic?
5. **Design.** Boundaries, ownership, duplication, naming, error model,
   dependencies. Will the next change be easy?
6. **Types and contracts.** Public signatures, `Any` leaks, optionality,
   immutability, backwards compatibility.
7. **Performance.** Only where the change plausibly affects a hot path; ask for
   measurement rather than speculation.
8. **Operations.** Config, migrations, logging, metrics, rollout, rollback.
9. **Style and consistency.** Let Ruff decide. Comment only where automation
   cannot.

## What to look for

### Correctness

- Errors are handled where they can be acted on; nothing important is swallowed.
- Resources are closed (`with`, `finally`, lifespan).
- Mutability is intentional; shared state is not mutated across threads/tasks.
- Time is timezone-aware and injected; random is seeded or cryptographic as
  required.
- Boundary values: zero, one, many, max, negative, empty, missing, duplicate.
- Return types are consistent; no `None` sneaking through a non-optional path.
- Async functions actually await I/O, and blocking calls are offloaded.

### Security

- All input is validated at the boundary.
- Authorization is checked per object, not only per route.
- SQL/commands/templates are parameterized or escaped.
- No `eval`, `exec`, unsafe pickle/YAML, or `shell=True` with untrusted data.
- Secrets are not in code, logs, or error messages.
- New dependencies are justified and locked.

### Tests

- The test fails without the production change.
- Tests assert behavior, not implementation details or log prose.
- Failure paths and edge cases are covered, not just the happy path.
- No sleeps, live network calls, or dependence on test order.
- Mocks are limited to boundaries and use `spec=`.

### Design

- Each new module has a clear responsibility and owner.
- Business logic is not embedded in handlers, ORM models, or tasks.
- Public API is minimal; internals are not exported by accident.
- Duplication is removed only when the abstraction is real.
- Errors are typed and translated at the edge.
- Naming states intent, not mechanism.

### Types

- Public functions are fully annotated.
- `Any` and `# type: ignore` are justified and narrow.
- Data models make invalid states impossible.
- Optional values are handled explicitly.
- Changes to public types are backward compatible or versioned.

### Operations

- Migration is reversible or has a documented rollback.
- New config has validation, defaults, and documentation.
- Logs and metrics make failure visible.
- Rate limits, timeouts, and retry behavior are defined for new I/O.
- Feature can be disabled without a redeploy if it is risky.

## Comment format

Report findings by severity and make each one actionable:

```text
[blocker] src/orders.py:42 — Authorization is checked on the route but not on
the order ID. Any authenticated user can read another tenant's order.
Add an ownership check in the query and a test for cross-tenant access.

[suggestion] src/orders.py:88 — This retry has no jitter and no cap, so all
workers retry in lockstep during an outage. Consider exponential backoff with
jitter, or reuse the client's policy.

[nit] tests/test_orders.py:12 — Prefer `pytest.param(..., id="expired-token")`
so the failure names the case.
```

Severity guide:

| Level | Meaning |
| --- | --- |
| blocker | Bug, security issue, data loss, broken contract; must fix |
| major | Likely incident or significant maintenance cost; should fix now |
| suggestion | Improvement with a clear rationale; author decides |
| nit | Style or preference; never blocks |
| question | Genuine uncertainty; ask, do not assert |

Rules:

- One issue per comment, with file and line.
- Explain the risk, not just the rule. Link to docs when it is obscure.
- Suggest a direction, not necessarily full code.
- Praise specific good decisions; it calibrates what to repeat.
- Do not restate what the diff already shows.
- Separate blocking from optional clearly so the author knows where they stand.

## Reviewing a large diff

- Read it in commits or logical slices, not alphabetically by file.
- Start with tests and public interfaces; they state intent.
- Skim generated, vendored, and lockfile changes; verify provenance instead.
- Check deleted code: was its behavior covered elsewhere?
- Look for unrelated changes; they increase risk and should be split.
- If the design is wrong, stop line-by-line review and discuss the design first.

## Red flags

- A PR that changes behavior without a test.
- `except Exception` added near a failing call.
- A new dependency for a few lines of code.
- A global cache without eviction.
- A timeout removed or set to `None`.
- A migration with no rollback.
- Auth logic duplicated in a second place.
- A public signature changed without a compatibility plan.
- A test that asserts on a mock call instead of an outcome.
- A "temporary" workaround with no issue reference.

## Before approving

- [ ] CI is green on the required checks.
- [ ] The change matches its stated scope.
- [ ] Tests cover the new behavior and its failure modes.
- [ ] Security-sensitive changes were reviewed against the safety checklist.
- [ ] Public API, schema, and config changes are documented.
- [ ] Rollout and rollback are understood.
- [ ] Remaining comments are non-blocking and labeled as such.

Approve when the change improves the codebase and remaining risks are
understood. Do not approve merely because the diff is small or the author is
senior.

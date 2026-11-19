---
name: Angular Testing
description: Test Angular applications with Vitest, TestBed, signal inputs, HttpTestingController, RouterTestingHarness, component harnesses, Playwright end-to-end tests, and deterministic CI. Use when adding tests, fixing flaky tests, or deciding what to mock.
---

# Angular Testing

Tests exist to make change safe. Test behavior through public interfaces, keep
the default suite fast, and use a real browser only where a real browser is the
point.

## Strategy

| Layer | Tool | What it proves |
| --- | --- | --- |
| Pure logic | Vitest | Rules, formatting, reducers, validators |
| Component | Vitest + TestBed | Inputs, outputs, rendering, user events |
| Feature integration | TestBed + router/HTTP testing | Route wiring, state, API mapping |
| End-to-end | Playwright | Critical journeys in a real browser |

- Test the contract, not private methods.
- Cover empty, one, many, maximum, invalid, unauthorized, loading, and error
  states.
- Every bug fix starts with a failing regression test.
- Prefer a few integration tests over dozens of mock-heavy unit tests.
- Keep the default suite under a few seconds per test file. Move slow browser
  work to Playwright.
- One behavior per test. Multiple assertions are fine when they describe one
  outcome.

## Vitest setup

Angular 21+ uses Vitest through the Angular CLI. New projects need no manual
runner setup.

```sh
ng test                 # watch mode
ng test --watch=false   # CI
ng test --coverage
```

- Do not add Karma or Jasmine to a new project.
- Configure coverage thresholds in the test target or `vitest.config.ts`,
  whichever the CLI version supports. Fail CI below the threshold.
- Keep `test-setup.ts` for global test configuration only. Do not hide app
  providers there.
- If the app is zoneless, ensure the test environment uses zoneless change
  detection (`provideZonelessChangeDetection()` where the CLI does not already
  configure it) and prefer `await fixture.whenStable()` over Zone-dependent
  timing.
- Use `vi.fn()`, `vi.spyOn()`, and `vi.useFakeTimers()`.

## Component tests

```ts
import { TestBed } from '@angular/core/testing';
import { UserBadge } from './user-badge';

describe('UserBadge', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserBadge],
    }).compileComponents();
  });

  it('renders the name and emits remove', async () => {
    const fixture = TestBed.createComponent(UserBadge);
    fixture.componentRef.setInput('name', 'Ada');
    await fixture.whenStable();

    const removed = vi.fn();
    fixture.componentInstance.removed.subscribe(removed);

    const button = fixture.nativeElement.querySelector('button') as HTMLButtonElement;
    expect(fixture.nativeElement.textContent).toContain('Ada');
    expect(button.getAttribute('aria-label')).toBe('Remove Ada');

    button.click();
    expect(removed).toHaveBeenCalledOnce();
  });
});
```

- Import standalone components in `imports`; do not declare them.
- Set signal inputs with `componentRef.setInput()`, not by assigning fields.
- Await `whenStable()` after changing inputs or triggering async work.
- Query by role or accessible name when possible. Avoid CSS classes as the
  primary selector.
- Dispatch real events (`click()`, `input` with a value) instead of calling
  component methods when testing user behavior.
- Do not assert internal signal values that the user cannot observe unless the
  signal is the public contract.

## Testing signals and effects

```ts
it('recomputes the total when quantity changes', async () => {
  const fixture = TestBed.createComponent(CartLine);
  fixture.componentRef.setInput('unitPriceCents', 500);
  fixture.componentRef.setInput('quantity', 2);
  await fixture.whenStable();

  expect(fixture.componentInstance.totalCents()).toBe(1000);

  fixture.componentRef.setInput('quantity', 3);
  await fixture.whenStable();

  expect(fixture.componentInstance.totalCents()).toBe(1500);
});
```

- Effects run asynchronously. Use `await fixture.whenStable()` before asserting.
- Use `TestBed.tick()` when you need to advance the scheduler explicitly.
- Avoid `fakeAsync`/`tick` unless you are testing timer behavior; it is brittle
  with zoneless and real async.

## Services and HTTP

```ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { OrderApi } from './order-api';

describe('OrderApi', () => {
  let api: OrderApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(OrderApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('maps the order list', () => {
    let result: Order[] | undefined;
    api.list({ status: 'all', page: 1 }).subscribe((orders) => (result = orders));

    const request = http.expectOne('/api/orders?page=1&status=all');
    expect(request.request.method).toBe('GET');
    request.flush([{ id: '1', status: 'paid', totalCents: 100 }]);

    expect(result?.[0]?.id).toBe('1');
  });
});
```

- Always call `http.verify()` in `afterEach` to catch unexpected requests.
- Flush errors explicitly and assert the mapped user-facing message.
- Test the API adapter's URL, method, body, and error mapping. Do not re-test
  `HttpClient`.
- Use `provideHttpClientTesting()`; never hit the network from unit tests.

## Router tests

```ts
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from './app.routes';

it('renders the order list route', async () => {
  TestBed.configureTestingModule({
    providers: [provideRouter(routes)],
  });

  const harness = await RouterTestingHarness.create();
  const component = await harness.navigateByUrl('/orders', OrderListPage);

  expect(component).toBeInstanceOf(OrderListPage);
  expect(TestBed.inject(Router).url).toBe('/orders');
});
```

- Use `RouterTestingHarness` instead of spying on `Router`.
- Test guards and resolvers as functions with a `TestBed` injection context.
- Assert redirects, wildcard routes, and lazy route loading.
- For query-param behavior, navigate and assert the component inputs and URL.

## Component harnesses

Angular Material, CDK, and Angular Aria ship test harnesses. Use them instead of
reaching into DOM structure.

```ts
import { HarnessLoader } from '@angular/cdk/testing';
import { TestbedHarnessEnvironment } from '@angular/cdk/testing/testbed';
import { MatButtonHarness } from '@angular/material/button/testing';

let loader: HarnessLoader;

beforeEach(() => {
  loader = TestbedHarnessEnvironment.loader(fixture);
});

it('submits with the primary button', async () => {
  const button = await loader.getHarness(MatButtonHarness.with({ text: 'Save' }));
  await button.click();
  expect(save).toHaveBeenCalled();
});
```

Harnesses survive markup changes and encode accessibility expectations.

## Playwright end-to-end

```ts
import { test, expect } from '@playwright/test';

test('customer can place an order', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('customer@example.com');
  await page.getByLabel('Password').fill('correct horse battery staple');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await page.getByRole('link', { name: 'New order' }).click();
  await page.getByLabel('SKU').fill('SKU-1');
  await page.getByLabel('Quantity').fill('2');
  await page.getByRole('button', { name: 'Place order' }).click();

  await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();
});
```

- Use user-facing locators: role, label, text. Avoid CSS and XPath.
- Test a small number of critical journeys: sign-in, checkout, the core CRUD
  flow, and one failure path.
- Seed data through an API or a test fixture, not by clicking through setup.
- Reuse authentication with `storageState`; do not log in for every test.
- Mock third-party services at the network boundary; keep your own backend real
  when feasible.
- Capture trace, screenshot, and video on failure only.
- Run in CI with a fixed browser version and retries limited to one.

## What not to test

- Framework behavior (`@if`, `@for`, signal scheduling).
- Private methods and internal fields.
- Exact DOM snapshots that change with styling.
- Third-party library internals.
- Every getter or one-line computed value.
- Implementation details that make refactoring painful.

## Determinism

- No real network, real clock, or shared mutable database in unit tests.
- Freeze time with `vi.useFakeTimers()` and restore in `afterEach`.
- Generate IDs through an injected token or a deterministic factory.
- Clean up `TestBed` between tests; do not leak providers or overrides.
- Isolate tests so they pass in any order and in parallel.
- Treat a flaky test as a bug; fix or delete it. Do not retry it into silence.

## Coverage

- Use coverage to find untested branches, not as a target to game.
- Set thresholds per project, not per file.
- Do not exclude files just to raise the number.
- Prioritize domain rules, error mapping, guards, and state transitions.
- A high-coverage suite that asserts nothing is worse than a smaller honest one.

## Anti-patterns

- Karma/Jasmine in a new Angular project.
- Testing private methods.
- `fixture.detectChanges()` everywhere instead of awaiting stability.
- Spying on `Router` or `HttpClient` instead of using testing providers.
- Hitting a real API from a unit test.
- `setTimeout` in tests.
- Snapshot tests of entire templates.
- Tests that depend on execution order.
- Mocking the feature under test.
- No assertion on the error path.
- E2E tests that cover every validation rule.
- Retrying flaky tests without investigating.

## Checklist

- [ ] Vitest runs locally and in CI with `--watch=false`.
- [ ] Component tests set inputs and assert user-visible behavior.
- [ ] Async tests await stability; no arbitrary sleeps.
- [ ] HTTP tests use `HttpTestingController` and verify outstanding requests.
- [ ] Router tests use `RouterTestingHarness`.
- [ ] Guards, resolvers, and error paths are covered.
- [ ] Material/CDK/Aria components are tested through harnesses.
- [ ] Playwright covers the critical journeys with user-facing locators.
- [ ] E2E seeds data and reuses auth state.
- [ ] Tests are isolated and deterministic.
- [ ] Coverage thresholds exist and reflect real risk.
- [ ] A failing test blocks merge.

## References

- `references/testing-recipes.md` — Vitest config, component, HTTP, router,
  harness, and Playwright examples.

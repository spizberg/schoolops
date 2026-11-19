# Testing recipes

## `angular.json` test target

```jsonc
{
  "projects": {
    "web": {
      "architect": {
        "test": {
          "builder": "@angular/build:unit-test",
          "options": {
            "tsConfig": "tsconfig.spec.json",
            "coverage": true,
            "coverageThresholds": {
              "statements": 80,
              "branches": 75,
              "functions": 80,
              "lines": 80
            }
          }
        }
      }
    }
  }
}
```

Builder and option names vary by Angular minor. Inspect `ng test --help` and the
generated `angular.json` before copying this block.

## Component test with signals

```ts
import { TestBed } from '@angular/core/testing';
import { QuantityPicker } from './quantity-picker';

describe('QuantityPicker', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [QuantityPicker] }).compileComponents();
  });

  it('clamps the value and emits the change', async () => {
    const fixture = TestBed.createComponent(QuantityPicker);
    fixture.componentRef.setInput('value', 99);
    fixture.componentRef.setInput('max', 99);
    await fixture.whenStable();

    const changed = vi.fn();
    fixture.componentInstance.changed.subscribe(changed);

    const increment = fixture.nativeElement.querySelectorAll('button')[1] as HTMLButtonElement;
    increment.click();
    await fixture.whenStable();

    expect(fixture.componentInstance.value()).toBe(99);
    expect(changed).not.toHaveBeenCalled();
  });
});
```

## Testing a form

```ts
import { TestBed } from '@angular/core/testing';
import { Login } from './login';

it('shows an email error after blur and blocks submit', async () => {
  const fixture = TestBed.createComponent(Login);
  await fixture.whenStable();

  const email = fixture.nativeElement.querySelector('input[type=email]') as HTMLInputElement;
  email.dispatchEvent(new Event('blur'));
  await fixture.whenStable();

  expect(fixture.nativeElement.textContent).toContain('Email is required');

  const submit = fixture.nativeElement.querySelector('button[type=submit]') as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
});
```

Prefer asserting rendered messages and button state over reading the form model.

## HTTP adapter test

```ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
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

  it('sends filters as query params', () => {
    api.list({ status: 'paid', page: 2 }).subscribe();

    const request = http.expectOne((req) => req.url === '/api/orders');
    expect(request.request.params.get('status')).toBe('paid');
    expect(request.request.params.get('page')).toBe('2');
    request.flush([]);
  });

  it('surfaces a server error', () => {
    const error = vi.fn();
    api.list({ status: 'all', page: 1 }).subscribe({ error });

    http
      .expectOne((req) => req.url === '/api/orders')
      .flush({ message: 'boom' }, { status: 500, statusText: 'Server Error' });

    expect(error).toHaveBeenCalled();
  });
});
```

## Router test

```ts
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from './app.routes';
import { OrderListPage } from './features/orders/feature/order-list-page';

it('navigates to the orders list', async () => {
  TestBed.configureTestingModule({ providers: [provideRouter(routes)] });

  const harness = await RouterTestingHarness.create();
  const component = await harness.navigateByUrl('/orders', OrderListPage);

  expect(component).toBeInstanceOf(OrderListPage);
  expect(TestBed.inject(Router).url).toBe('/orders');
});
```

## Guard test

```ts
import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { authGuard } from './auth.guard';
import { Auth } from './auth';

it('redirects anonymous users to login', () => {
  TestBed.configureTestingModule({
    providers: [
      { provide: Auth, useValue: { isAuthenticated: () => false } },
      { provide: Router, useValue: { createUrlTree: () => ({}) as UrlTree } },
    ],
  });

  const result = TestBed.runInInjectionContext(() =>
    authGuard({} as never, {} as never),
  );

  expect(result).toBeInstanceOf(Object);
});
```

Prefer testing the guard through a real router navigation when practical.

## Playwright configuration

```ts
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0,
  workers: process.env['CI'] ? 2 : undefined,
  reporter: process.env['CI'] ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env['E2E_BASE_URL'] ?? 'http://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: process.env['E2E_BASE_URL']
    ? undefined
    : {
        command: 'npm start -- --port 4200',
        url: 'http://localhost:4200',
        reuseExistingServer: !process.env['CI'],
        timeout: 120_000,
      },
});
```

## Authenticated E2E without logging in every test

```ts
// e2e/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env['E2E_USER']!);
  await page.getByLabel('Password').fill(process.env['E2E_PASSWORD']!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
```

```ts
// playwright.config.ts (excerpt)
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
    dependencies: ['setup'],
  },
]
```

Add `e2e/.auth/` to `.gitignore`. Never commit credentials.

## Accessibility test in the browser

```ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('checkout has no critical a11y violations', async ({ page }) => {
  await page.goto('/checkout');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
    .analyze();

  expect(results.violations).toEqual([]);
});
```

Treat critical and serious violations as build failures; triage moderate ones.

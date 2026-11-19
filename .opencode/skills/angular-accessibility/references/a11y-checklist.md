# Accessibility recipes

## Skip link

```html
<a class="skip-link" href="#main-content">Skip to main content</a>
```

```css
.skip-link {
  position: absolute;
  left: 1rem;
  top: -3rem;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  color: var(--color-text);
  z-index: 100;
  transition: top 150ms ease;
}

.skip-link:focus {
  top: 1rem;
}
```

The target needs `tabindex="-1"` so it can receive programmatic focus:

```html
<main id="main-content" tabindex="-1">…</main>
```

## Route announcer

```ts
import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { LiveAnnouncer } from '@angular/cdk/a11y';
import { NavigationEnd, Router } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { filter } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class RouteAnnouncer {
  private readonly router = inject(Router);
  private readonly announcer = inject(LiveAnnouncer);
  private readonly title = inject(Title);
  private readonly platform = inject(PLATFORM_ID);

  start(): void {
    if (!isPlatformBrowser(this.platform)) return;

    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(() => {
        queueMicrotask(() => {
          const heading = document.querySelector<HTMLElement>('main h1');
          if (heading) {
            heading.setAttribute('tabindex', '-1');
            heading.focus();
          }
          this.announcer.announce(`${this.title.getTitle()} page loaded`, 'polite');
        });
      });
  }
}
```

Call `start()` once during app initialization. Set a route `title` or update
`Title` when data resolves. The platform guard keeps the service safe under SSR.

## Dialog with focus trap and restore

```ts
import { Component, output } from '@angular/core';
import { A11yModule } from '@angular/cdk/a11y';

@Component({
  selector: 'app-confirm-dialog',
  imports: [A11yModule],
  template: `
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      cdkTrapFocus
      [cdkTrapFocusAutoCapture]="true"
    >
      <h2 id="confirm-title">Delete this order?</h2>
      <p>This action cannot be undone.</p>
      <button type="button" cdkFocusInitial (click)="closed.emit(false)">Cancel</button>
      <button type="button" (click)="closed.emit(true)">Delete</button>
    </div>
  `,
})
export class ConfirmDialog {
  readonly closed = output<boolean>();
}
```

When you open this from a parent, store the trigger element and restore focus on
close. `@angular/cdk/dialog` handles the trap and restore for you; prefer it over
a custom overlay.

## Tabs with Angular Aria

```ts
import { Component, signal } from '@angular/core';
import { Tab, TabContent, TabList, TabPanel, Tabs } from '@angular/aria/tabs';

@Component({
  selector: 'app-settings-tabs',
  imports: [Tabs, TabList, Tab, TabPanel, TabContent],
  template: `
    <div ngTabs>
      <div ngTabList selectionMode="follow" [(selectedTab)]="selected">
        <div ngTab value="profile">Profile</div>
        <div ngTab value="billing">Billing</div>
        <div ngTab value="security">Security</div>
      </div>

      <div ngTabPanel value="profile">
        <ng-template ngTabContent>Profile settings</ng-template>
      </div>
      <div ngTabPanel value="billing">
        <ng-template ngTabContent>Billing settings</ng-template>
      </div>
      <div ngTabPanel value="security">
        <ng-template ngTabContent>Security settings</ng-template>
      </div>
    </div>
  `,
})
export class SettingsTabs {
  readonly selected = signal('profile');
}
```

The primitive owns arrow-key navigation, roving tabindex, `aria-selected`, and
lazy panel rendering. Use `selectionMode="explicit"` for heavy panels that should
not render until the user activates them.

## Accessible form errors

```html
<form (submit)="onSubmit($event)" novalidate>
  @if (summary().length) {
    <div role="alert" tabindex="-1" #summary>
      <p>Please fix {{ summary().length }} fields.</p>
      <ul>
        @for (item of summary(); track item.field) {
          <li><a [href]="'#' + item.field">{{ item.message }}</a></li>
        }
      </ul>
    </div>
  }

  <label for="email">Email</label>
  <input
    id="email"
    type="email"
    [formField]="form.email"
    [attr.aria-invalid]="form.email().touched() && form.email().invalid()"
    [attr.aria-describedby]="form.email().touched() && form.email().invalid() ? 'email-error' : null"
  />
  @if (form.email().touched() && form.email().invalid()) {
    <p id="email-error" role="alert">{{ form.email().errors()[0]?.message }}</p>
  }

  <button type="submit">Save</button>
</form>
```

On submit failure, focus the summary or the first invalid field.

## Live status

```html
<p role="status" aria-live="polite">
  @if (saving()) { Saving… } @else if (saved()) { Saved }
</p>
```

- `role="status"` implies `aria-live="polite"`.
- `role="alert"` implies `aria-live="assertive"`; use it sparingly.
- Keep the live region in the DOM before the message changes. Inserting the
  whole region at once may not be announced.
- Do not announce every keystroke.

## Icon-only button

```html
<button type="button" (click)="close()">
  <svg aria-hidden="true" focusable="false">…</svg>
  <span class="visually-hidden">Close dialog</span>
</button>
```

```css
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

Prefer visually hidden text over `aria-label` for translatable strings; both are
valid.

## Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Do not remove essential state changes; make them instant.

## axe in Playwright

```ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const routes = ['/', '/orders', '/checkout', '/settings'];

for (const route of routes) {
  test(`${route} has no critical accessibility violations`, async ({ page }) => {
    await page.goto(route);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
      .analyze();

    const serious = results.violations.filter(
      (violation) => violation.impact === 'critical' || violation.impact === 'serious',
    );
    expect(serious).toEqual([]);
  });
}
```

## Manual test script

1. Tab through the page from the top. Every control is reachable and visible.
2. Operate each control with Enter/Space/arrow keys as appropriate.
3. Open and close every dialog; focus returns to the trigger.
4. Submit an invalid form; focus lands on the error summary or first error.
5. Navigate between routes; title changes, focus moves, and the page is
   announced.
6. Zoom to 200%; no content is clipped or hidden.
7. Enable reduced motion; no essential animation remains.
8. Run a screen reader through the primary journey.

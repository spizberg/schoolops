---
name: Angular Accessibility
description: Build accessible Angular interfaces with semantic HTML, Angular Aria, CDK focus management, live announcements, keyboard support, form error wiring, and automated axe checks. Use when building interactive components, route transitions, dialogs, or an accessibility review.
---

# Angular Accessibility

Accessibility is correctness. A component that cannot be operated by keyboard or
understood by a screen reader is broken for real users, not a nice-to-have.

Target WCAG 2.2 AA unless the product has a stricter legal requirement.

## Semantics first

- Use the element that already has the behavior: `button`, `a`, `input`,
  `select`, `textarea`, `dialog`, `details`, `fieldset`, `table`.
- A clickable `div` or `span` needs a role, tab stop, key handling, and focus
  styles. A `button` needs none of that.
- Use landmarks: `header`, `nav`, `main`, `aside`, `footer`. One `main` per page.
- Use one `h1` per page and do not skip heading levels for styling.
- Use lists for lists and tables for tabular data. Do not fake layout with them.
- `aria-*` describes what HTML cannot. It does not add behavior.

## Angular Aria

Angular Aria is stable in Angular 22 and provides twelve accessible UI patterns
with styling left to you: accordion, autocomplete, combobox, grid, listbox,
menu, menubar, multiselect, select, tabs, toolbar, and tree. It ships in the
`@angular/aria` package:

```sh
npm install @angular/aria
```

```ts
import { Component } from '@angular/core';
import {
  AccordionContent,
  AccordionGroup,
  AccordionPanel,
  AccordionTrigger,
} from '@angular/aria/accordion';

@Component({
  selector: 'app-faq',
  imports: [AccordionGroup, AccordionTrigger, AccordionPanel, AccordionContent],
  template: `
    <div ngAccordionGroup [multiExpandable]="false">
      @for (item of items; track item.id) {
        <h3>
          <span ngAccordionTrigger [panel]="panel">
            {{ item.question }}
          </span>
        </h3>
        <div ngAccordionPanel #panel="ngAccordionPanel">
          <ng-template ngAccordionContent>{{ item.answer }}</ng-template>
        </div>
      }
    </div>
  `,
})
export class Faq {}
```

Prefer Angular Aria or Angular Material over hand-rolled ARIA widgets. They
encode keyboard interaction, focus order, and announcements that are easy to get
wrong.

## CDK utilities

- `cdkTrapFocus` traps focus inside dialogs and drawers.
- `cdkFocusInitial` sets the initial focus target.
- `LiveAnnouncer` announces status changes and route transitions.
- `FocusMonitor` tracks keyboard vs mouse focus for styling.
- `A11yModule` provides these directives.

Angular Aria covers the widget patterns; CDK covers the lower-level focus,
overlay, and announcement utilities. Use both rather than reimplementing either.

```html
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="dialog-title"
  cdkTrapFocus
  [cdkTrapFocusAutoCapture]="true"
>
  <h2 id="dialog-title">Delete order</h2>
  <p>This cannot be undone.</p>
  <button type="button" cdkFocusInitial (click)="cancel()">Cancel</button>
  <button type="button" (click)="confirm()">Delete</button>
</div>
```

- Always restore focus to the trigger when the dialog closes.
- Do not use `aria-modal` without trapping focus and hiding the background from
  assistive technology.
- Prefer the native `<dialog>` element or Angular CDK dialog over a custom
  overlay.

## Keyboard support

- Every interactive element is reachable by Tab and operable by Enter/Space.
- Logical tab order follows visual order. Do not use positive `tabindex`.
- Escape closes dialogs, menus, and popovers.
- Arrow keys move within composite widgets (tabs, menus, listboxes, grids).
- Do not create keyboard traps. A dialog trap must be escapable.
- Provide a visible focus indicator with sufficient contrast.
- Support skip links to bypass repeated navigation.

```html
<a class="skip-link" href="#main-content">Skip to main content</a>
<nav>…</nav>
<main id="main-content" tabindex="-1">…</main>
```

## Route changes

Single-page navigation does not reset focus or announce the new page by default.

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
        const heading = document.querySelector<HTMLElement>('main h1');
        if (heading) {
          heading.setAttribute('tabindex', '-1');
          heading.focus();
        }
        this.announcer.announce(`${this.title.getTitle()} page loaded`, 'polite');
      });
  }
}
```

- Update the document title on every route.
- Move focus to the `main` heading or container after navigation.
- Announce once, politely. Do not announce every intermediate router event.
- Ensure the skip link and navigation remain reachable after the transition.

## Forms

- Every control has a visible `<label>` or an accessible name.
- Group related controls with `fieldset`/`legend`.
- Set `aria-invalid="true"` on invalid fields.
- Link errors with `aria-describedby`; keep the error text in the DOM.
- Use `role="alert"` for submit-level errors and `role="status"` for async
  progress.
- On a failed submit, focus the first invalid field or an error summary.
- Do not disable submit silently; explain what is missing.
- Do not use placeholder text as a label.
- Mark required fields in text, not only with an asterisk or color.

```html
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
```

## Images, icons, and media

- Content images need meaningful `alt` text.
- Decorative images use `alt=""`, not a missing `alt`.
- Icon-only buttons need an accessible name (`aria-label` or visually hidden
  text).
- Decorative icons inside a labeled control use `aria-hidden="true"`.
- Video needs captions; audio needs transcripts.
- Do not autoplay audio.

## Motion, color, and size

- Respect `prefers-reduced-motion` for non-essential animation.
- Do not convey information by color alone. Add text, icons, or patterns.
- Meet contrast: 4.5:1 for normal text, 3:1 for large text and UI boundaries.
- Support 200% zoom and 320px reflow without loss of content.
- Target size is at least 24×24 CSS pixels (WCAG 2.2), with adequate spacing.
- Do not remove focus outlines; replace them with a visible style.

## Testing

- Run `axe-core` in component and E2E tests for automated coverage.
- Test every interactive flow with the keyboard only.
- Test with a screen reader: NVDA on Windows, VoiceOver on macOS/iOS, TalkBack
  on Android.
- Test at 200% zoom and with a mobile viewport.
- Test with reduced motion enabled.
- Use Angular Aria/Material test harnesses to assert accessibility behavior.
- Automated tools catch roughly a third of issues; manual testing is required.

```ts
import AxeBuilder from '@axe-core/playwright';

const results = await new AxeBuilder({ page })
  .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
  .analyze();

expect(results.violations).toEqual([]);
```

## Anti-patterns

- Clickable `div`/`span` without role, tab stop, and key handling.
- `aria-label` on a non-interactive element with no role.
- Positive `tabindex`.
- Removing focus outlines.
- Placeholder used as a label.
- Errors shown only by red border.
- `aria-hidden="true"` on focusable content.
- Dialog without focus trap and focus restore.
- Route change with no title update or focus move.
- Autoplay video or audio.
- Color-only status indicators.
- Custom widget with no keyboard support.
- Assuming axe passing means accessible.

## Checklist

- [ ] Semantic elements are used before ARIA.
- [ ] Landmarks, headings, and page title are correct.
- [ ] Angular Aria/Material/CDK is used for complex widgets.
- [ ] All interactive elements are keyboard operable in visual order.
- [ ] Focus is visible, trapped only in dialogs, and restored on close.
- [ ] Route changes update the title, announce, and move focus.
- [ ] Forms have labels, error associations, and a submit error path.
- [ ] Images and icons have correct `alt`/`aria-hidden`.
- [ ] Contrast, zoom, reflow, target size, and reduced motion are handled.
- [ ] axe checks run in CI with no critical or serious violations.
- [ ] A manual keyboard and screen-reader pass is part of release.
- [ ] Accessibility acceptance criteria exist for new UI.

## References

- `references/a11y-checklist.md` — route announcer, dialog, tabs, form errors,
  skip link, and axe test recipes.

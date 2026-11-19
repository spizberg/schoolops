---
name: Angular Project Setup
description: Bootstrap and standardize a production Angular workspace with the CLI, strict TypeScript, ESLint, Prettier, Vitest, typed environment config, budgets, and CI. Use when creating an Angular app, adding tooling, or making a workspace production-ready.
---

# Angular Project Setup

A production workspace is one where a new contributor clones, installs, and runs
one command to get the same format, lint, type, test, and build results as CI.
Everything else is detail.

This skill targets Angular 22 and later. The framework is on a yearly major
cadence after v22, so verify the installed version before copying config.

## Baseline stack

| Concern | Default | Notes |
| --- | --- | --- |
| Framework | Angular 22+ | Standalone, zoneless, OnPush by default |
| Node | Active LTS | Pin with `.nvmrc` and `engines` |
| Package manager | `npm` or `pnpm` | Commit the lockfile, use one |
| Language | TypeScript strict | Add template strictness |
| Lint | `angular-eslint` flat config | Type-aware rules and template a11y |
| Format | Prettier | One config, no debates |
| Unit tests | Vitest via `ng test` | Default since v21 |
| E2E | Playwright | User-facing locators |
| Build | `@angular/build` application builder | Webpack builders are deprecated |
| SSR | Opt-in | Add for SEO, first paint, or public content |

Do not add Nx, a state library, a UI kit, or SSR on day one unless a requirement
demands it. Every layer you add before you need it is a decision you must
maintain.

## Create the workspace

```sh
ng new web --style=scss --ssr=false --package-manager=pnpm
cd web
```

- Keep the CLI defaults for standalone, zoneless, and Vitest unless you have a
  documented reason not to.
- Enable SSR with `ng add @angular/ssr` when the app needs crawlable content,
  fast first paint on slow devices, or per-request rendering. Do not enable it
  "just in case"; it changes deployment, testing, and browser API rules.
- Use one repository per deployable application. Add `ng generate library` only
  when code is genuinely shared by multiple apps.
- Do not hand-roll `package.json`, `angular.json`, or `tsconfig.json` when the
  CLI can generate them; upgrade paths assume the generated shape.

## Workspace layout

```text
web/
├── angular.json
├── eslint.config.js
├── package.json
├── playwright.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.spec.json
├── public/
└── src/
    ├── index.html
    ├── main.ts
    ├── styles.scss
    └── app/
        ├── app.ts
        ├── app.html
        ├── app.config.ts
        ├── app.routes.ts
        ├── core/
        ├── shared/
        ├── layout/
        └── features/
```

- `core/` holds app-wide singletons: auth, configuration, HTTP setup, error
  handling. It must not import features.
- `shared/` holds reusable, stateless UI and utilities. It must not import
  features or `core`.
- `features/` owns product capabilities. A feature may import `shared` and
  `core`, never another feature's internals.
- Keep `main.ts` and `app.config.ts` thin. Bootstrap only.

## Strict TypeScript

Angular generates `strict: true`. Add the checks that catch real bugs:

```jsonc
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true
  },
  "angularCompilerOptions": {
    "strictTemplates": true,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "typeCheckHostBindings": true
  }
}
```

- `strictTemplates` is non-negotiable. It catches template typos that would
  otherwise become runtime errors.
- `noUncheckedIndexedAccess` forces you to handle missing array and record
  entries. It is noisy at first and worth it in production code.
- Do not weaken strictness to silence a library's types. Fix the boundary with
  a narrow adapter or a declaration file.
- Keep one `tsconfig.json` for shared options and thin `tsconfig.app.json` /
  `tsconfig.spec.json` files for environment-specific settings.

## Lint and format

Use `angular-eslint` flat config with type-aware rules and template
accessibility. Run Prettier separately; do not let ESLint format.

```js
// eslint.config.js
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import angular from 'angular-eslint';

export default tseslint.config(
  {
    files: ['**/*.ts'],
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.strictTypeChecked,
      ...angular.configs.tsRecommended,
    ],
    languageOptions: {
      parserOptions: { projectService: true },
    },
    processor: angular.processInlineTemplates,
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
    },
  },
  {
    files: ['**/*.html'],
    extends: [
      ...angular.configs.templateRecommended,
      ...angular.configs.templateAccessibility,
    ],
  },
);
```

- Do not disable `no-floating-promises`; unhandled async work is a production
  bug.
- Template accessibility rules are cheaper than an audit later.
- Allow `any` only in a narrowly scoped adapter with a comment and an issue.

## Environment and configuration

Frontend configuration is public. Never put secrets, API keys with write access,
or private endpoints in the bundle.

- Use `environment.ts` only for build-time flags that differ per build
  (`production: true`, feature toggles baked at build).
- Use a runtime `config.json` for values that differ per deployment (API base
  URL, tenant, analytics key). Fetch and validate it before bootstrap:

```ts
// main.ts
bootstrapApplication(App, appConfig).catch((err) => console.error(err));
```

- For runtime config, load it in an `APP_INITIALIZER` or an async provider,
  validate with a schema, and expose it through an injection token. Fail fast on
  missing required values.
- With SSR, pass per-request config through the server, not a module-level
  mutable singleton.
- Type the config once and inject it. Do not read `window` or `process.env`
  throughout components.

## Budgets

Set budgets before the app grows. They turn bundle regressions into build
failures.

```jsonc
// angular.json
"budgets": [
  { "type": "initial", "maximumWarning": "400kB", "maximumError": "600kB" },
  { "type": "anyComponentStyle", "maximumWarning": "6kB", "maximumError": "10kB" }
]
```

Tighten them to your actual baseline plus a small margin. A budget nobody hits
is decoration; a budget that fails on every feature is ignored.

## Quality gate

One command must run everything CI runs:

```json
{
  "scripts": {
    "start": "ng serve",
    "build": "ng build",
    "lint": "ng lint",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit",
    "test": "ng test",
    "test:ci": "ng test --watch=false --coverage",
    "e2e": "playwright test",
    "check": "npm run format:check && npm run lint && npm run typecheck && npm run test:ci && npm run build"
  }
}
```

- CI runs `npm ci` (or `pnpm install --frozen-lockfile`), then `npm run check`.
- Do not auto-format in CI. Report violations; let the author fix them.
- Run E2E in a separate job after build, with browser caching.
- Upload coverage and Playwright reports only if someone reads them.
- Pin Node in CI to the same major as `.nvmrc`.

## Dependency policy

- Commit exactly one lockfile. Do not mix npm, pnpm, and yarn.
- Automate upgrades with Renovate or Dependabot; review major upgrades.
- Before adding a runtime dependency, check maintenance, license, bundle cost,
  and whether the framework or platform already covers it.
- Prefer Angular CDK and Angular Aria over bespoke interaction code.
- Avoid wrapper libraries that hide the framework; they age badly.
- Audit with `npm audit --omit=dev` in CI, but do not let a transitive advisory
  block every build without a triage path.

## Anti-patterns

- Disabling `strictTemplates` or `strict` to ship faster.
- No lockfile, or a lockfile that CI ignores.
- `environment.ts` holding an API secret.
- SSR enabled with no plan for browser-only APIs.
- A global state library before there is shared state.
- `any` sprinkled through services and templates.
- Lint rules disabled inline without a reason.
- A `check` script that differs from CI.
- Budgets set so high they never fire.
- Importing a whole UI kit for three components.
- Supporting Node versions no CI job runs.

## Checklist

- [ ] App generated by the CLI on a supported Angular and Node version.
- [ ] Lockfile committed; clean install works from a fresh clone.
- [ ] TypeScript and templates are strict.
- [ ] ESLint (type-aware + template a11y) and Prettier configured.
- [ ] Unit tests run with Vitest; E2E runs with Playwright.
- [ ] Runtime config is validated and injected, not read ad hoc.
- [ ] No secret is present anywhere in the client bundle.
- [ ] Initial and component style budgets are set and realistic.
- [ ] One `check` command is documented and used by CI.
- [ ] `README.md` shows install, run, test, and build commands that work.
- [ ] `.gitignore` excludes build output, coverage, and local env files.

## References

- `references/workspace-skeleton.md` — config files, scripts, and CI pipeline.

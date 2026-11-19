# Angular workspace skeleton

Concrete files for a production Angular 22 workspace. Adapt names and versions;
keep the boundaries and the single quality gate.

## Commands

```sh
ng new web --style=scss --ssr=false --package-manager=pnpm
cd web
pnpm add -D prettier eslint @eslint/js typescript-eslint angular-eslint
pnpm add -D @playwright/test
pnpm exec playwright install
```

Add SSR only when required:

```sh
ng add @angular/ssr
```

## `package.json`

```json
{
  "name": "web",
  "version": "0.0.0",
  "private": true,
  "engines": { "node": ">=22.0.0" },
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

## `tsconfig.json`

```jsonc
{
  "compileOnSave": false,
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "experimentalDecorators": true,
    "moduleResolution": "bundler",
    "importHelpers": true,
    "target": "ES2022",
    "module": "ES2022",
    "lib": ["ES2022", "dom"]
  },
  "angularCompilerOptions": {
    "strictTemplates": true,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "typeCheckHostBindings": true
  }
}
```

## `eslint.config.js`

```js
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

## `.prettierrc`

```json
{
  "singleQuote": true,
  "printWidth": 100,
  "overrides": [{ "files": "*.html", "options": { "parser": "angular" } }]
}
```

## `angular.json` budgets

```jsonc
{
  "projects": {
    "web": {
      "architect": {
        "build": {
          "configurations": {
            "production": {
              "budgets": [
                { "type": "initial", "maximumWarning": "400kB", "maximumError": "600kB" },
                { "type": "anyComponentStyle", "maximumWarning": "6kB", "maximumError": "10kB" }
              ]
            }
          }
        }
      }
    }
  }
}
```

## Runtime configuration

```ts
// src/app/core/config/app-config.ts
import { InjectionToken, inject } from '@angular/core';

export interface AppConfig {
  apiBaseUrl: string;
  environment: 'staging' | 'production';
  analyticsKey?: string;
}

export const APP_CONFIG = new InjectionToken<AppConfig>('APP_CONFIG');

export function provideAppConfig(config: AppConfig) {
  return { provide: APP_CONFIG, useValue: config };
}

export function injectAppConfig(): AppConfig {
  return inject(APP_CONFIG);
}
```

```ts
// src/app/core/config/load-config.ts
import { AppConfig } from './app-config';

export async function loadConfig(): Promise<AppConfig> {
  const response = await fetch('/assets/config.json', { cache: 'no-cache' });
  if (!response.ok) {
    throw new Error(`Config request failed: ${response.status}`);
  }
  const raw: unknown = await response.json();
  if (!isAppConfig(raw)) {
    throw new Error('Invalid runtime configuration');
  }
  return raw;
}

function isAppConfig(value: unknown): value is AppConfig {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v['apiBaseUrl'] === 'string' &&
    (v['environment'] === 'staging' || v['environment'] === 'production')
  );
}
```

Wire it before bootstrap so no component sees a half-configured app. With SSR,
resolve the same shape on the server per request.

## GitHub Actions

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npm run format:check
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test:ci
      - run: npm run build

  e2e:
    runs-on: ubuntu-latest
    needs: check
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - run: npm run e2e
```

## Repository files

```text
.nvmrc                 # e.g. 22
.gitignore             # dist/, coverage/, .angular/, playwright-report/
.editorconfig
.prettierrc
README.md              # install, run, test, build, deploy
```

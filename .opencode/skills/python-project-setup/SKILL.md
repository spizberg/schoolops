---
name: Python Project Setup
description: Bootstrap or standardize a Python project with uv, pyproject.toml, Ruff, strict type checking, pytest, pre-commit, and CI. Use when creating a project, adding dependencies or tooling, or making a repo production-ready.
---

# Python Project Setup

A project is production-ready when a new contributor can clone it, run one
command, and get the same lint, type, and test results as CI.

## Workflow

1. Inspect what already exists before adding tooling: `pyproject.toml`, lockfile,
   `justfile`, CI config, `.pre-commit-config.yaml`.
2. Choose the supported Python range. Do not claim support you do not test.
   Prefer the oldest version you must support, and test the newest too.
3. Put all tool configuration in `pyproject.toml` unless a tool requires its own
   file. One source of truth beats scattered dotfiles.
4. Pin the toolchain with a lockfile. Commit it.
5. Add one quality command that runs the same steps locally and in CI.
6. Verify from a clean environment: `uv sync --all-extras --dev` then the
   quality command.

## Baseline stack

| Concern | Default | Notes |
| --- | --- | --- |
| Env + deps | `uv` | Fast, lockfile-based, manages Python versions |
| Task runner | `just` | One `just check` command for local and CI |
| Lint + format | `ruff` | Replace flake8, isort, pyupgrade, and most plugins |
| Types | `mypy --strict` or `pyright` / `ty` | Strict from day one; loosening later is painful |
| Tests | `pytest` | Plus `pytest-cov`, `hypothesis` for tricky logic |
| Hooks | `pre-commit` | Run Ruff and fast tests before commit |
| CI | GitHub Actions or equivalent | Lint, type check, test across supported versions |
| Build | `hatchling` | Only if the project is a distributable package |

Do not add a dependency for something the standard library does well. Every
dependency is code you now own the upgrade risk for.

## Project layout

Use a `src/` layout for anything importable. It prevents importing the working
directory by accident and matches installed behavior.

```text
project/
├── pyproject.toml
├── uv.lock
├── README.md
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── py.typed
│       └── module.py
├── tests/
│   ├── conftest.py
│   └── test_module.py
└── .github/workflows/ci.yml
```

For an application rather than a library, `src/` is still recommended. Name the
package after the import name, not the repository name.

## Dependency policy

- Add runtime dependencies with `uv add <pkg>`; dev-only with
  `uv add --dev <pkg>`.
- Commit `uv.lock`. Use `uv lock --check` in CI.
- Review a new dependency before adding it: maintenance activity, license,
  transitive dependency count, and whether the stdlib covers the need.
- Pin application deployments with the lockfile; express libraries with
  compatible ranges. Never commit a `requirements.txt` generated ad hoc next to
  a lockfile.
- Run `uv sync --frozen` in CI so the lockfile is authoritative.

## Quality gate

Expose one command. A `justfile` is enough:

```just
# List available recipes
default:
    @just --list

# Check formatting and lint
lint:
    uv run ruff format --check .
    uv run ruff check .

# Type-check
type:
    uv run mypy src tests

# Run tests with coverage
test:
    uv run pytest --cov --cov-report=term-missing

# Full quality gate
check: lint type test
```

Recipes run sequentially in dependency order, so `just check` stops on the first
failure. Add a `#` comment above each recipe: `just` and `just --list` use them as
help text. `uv run` guarantees the tool runs in the project environment. Never
tell a contributor to activate a virtualenv manually.

## CI rules

- Run on the same commands as the quality gate; do not duplicate logic in YAML.
- Test every supported Python version with a matrix, plus the newest.
- Cache the uv cache, not the virtualenv.
- Fail on lint and type errors; do not auto-fix in CI.
- Run tests with `-W error` (or a curated filter) so new warnings are visible.
- Upload coverage or test reports only when they are actually consumed.

## Packaging notes

- Set `requires-python` to the range you test, e.g. `>=3.12`.
- Include `py.typed` and configure package discovery.
- Keep `__version__` in one place; derive it or read metadata.
- Build and inspect the wheel in CI (`uv build`, then check contents).
- Do not publish from untrusted branches; use trusted publishing or a token in
  a protected environment.

## Anti-patterns

- `pip install` in README while the project locks with uv.
- Loose `*` dependency pins in an application.
- `setup.py` plus `setup.cfg` plus `pyproject.toml`.
- Mypy config that ignores every third-party module with no follow-up.
- CI that formats code, hiding violations instead of reporting them.
- A `requirements-dev.txt` that drifts from the lockfile.
- Supporting Python versions no CI job runs.

## Checklist

- [ ] `pyproject.toml` declares metadata, dependencies, and all tool config.
- [ ] Lockfile committed; `uv sync --frozen` works from a clean clone.
- [ ] Ruff format and lint pass with a documented rule set.
- [ ] Type checking runs in strict mode on `src` and `tests`.
- [ ] `pytest` runs with warnings treated as errors.
- [ ] One quality command is documented and used by CI.
- [ ] `README.md` shows setup, run, and test commands that actually work.
- [ ] `.gitignore` excludes `.venv`, caches, coverage, and local env files.
- [ ] License and supported Python versions are explicit.

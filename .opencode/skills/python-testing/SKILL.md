---
name: Python Testing
description: Design fast, deterministic pytest suites with fixtures, parametrization, fakes, Hypothesis, async tests, and meaningful coverage. Use when adding tests, fixing flaky tests, or deciding what to mock.
---

# Python Testing

Tests exist to enable change. A slow, flaky suite that mirrors implementation
details is worse than a small suite of behavioral tests.

## Strategy

- Test behavior through public interfaces, not private helpers.
- Cover the boundaries: empty, one, many, maximum, invalid, and unauthorized.
- Every bug fix starts with a failing regression test.
- Prefer a few integration tests over dozens of mock-heavy unit tests.
- Keep the default suite fast (< 10 s); mark slow and external tests and run
  them in CI or on demand.
- One logical assertion per test, but multiple `assert`s are fine when they
  describe one outcome.

Test pyramid for a typical service:

| Layer | Count | Speed | What it proves |
| --- | --- | --- | --- |
| Unit / domain | Many | ms | Rules, edge cases, pure logic |
| Integration | Some | 100 ms–s | DB, HTTP handlers, serialization |
| End-to-end | Few | seconds+ | Critical user journeys |

## Structure

```text
tests/
├── conftest.py          # shared fixtures, no test cases
├── unit/
│   └── test_pricing.py
├── integration/
│   └── test_orders_api.py
└── e2e/
    └── test_checkout.py
```

Naming: `test_<behavior>_<condition>_<expected>` or a readable sentence. Test
files mirror the module they cover. Use `pytest.mark` for slow/integration/e2e.

## Arrange–Act–Assert

```python
def test_discount_applies_only_above_threshold() -> None:
    cart = Cart(items=[Item(price=100_00)])          # arrange
    price = cart.total_with_discount(threshold=200_00, percent=10)
    assert price == 100_00                            # act + assert
```

Keep the act to one call when possible. If setup dominates the test, extract a
factory fixture, not a helper that hides the assertion.

## Fixtures

- Fixtures provide state and dependencies; they do not contain assertions
  (except invariant checks).
- Default to function scope. Use session scope only for immutable, expensive
  resources.
- Use `yield` for teardown; never rely on test ordering.
- Prefer explicit factory functions over deeply nested fixture graphs.

```python
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

@dataclass
class FakeClock:
    now: datetime

@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 1, tzinfo=UTC))

@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.sqlite3")
    database.migrate()
    try:
        yield database
    finally:
        database.close()
```

Built-in fixtures to use instead of hand-rolling:

| Fixture | Use |
| --- | --- |
| `tmp_path` | Real filesystem, isolated per test |
| `monkeypatch` | Env vars, attributes, `chdir`, `sys.path` |
| `caplog` | Assert log records and levels |
| `capsys` | Assert stdout/stderr |
| `pytest.raises` | Assert exception type, message, and cause |
| `pytest.warns` | Assert warnings |
| `pytest.approx` | Float comparisons |

## Parametrization

```python
import pytest

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", 0),
        ("42", 42),
        ("-7", -7),
        pytest.param(" 12 ", 12, id="surrounding-whitespace"),
    ],
)
def test_parse_int(raw: str, expected: int) -> None:
    assert parse_int(raw) == expected

@pytest.mark.parametrize("raw", ["", "abc", "1.5", "--1"])
def test_parse_int_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_int(raw)
```

Use `pytest.param(..., id=...)` for cases worth naming, and `xfail` with
`strict=True` for known bugs. Avoid duplicate logical cases.

## Fakes before mocks

- Fake: a working, in-memory implementation of a protocol. Fast, reusable, no
  coupling to call order.
- Stub: returns canned values.
- Mock: asserts interactions. Use only when the interaction is the contract.

```python
class InMemoryUserRepo:
    def __init__(self) -> None:
        self._users: dict[UserId, User] = {}

    def get(self, id_: UserId) -> User | None:
        return self._users.get(id_)

    def add(self, user: User) -> None:
        self._users[user.id] = user
```

Mock third-party boundaries, not your own classes. When you must mock:

```python
from unittest.mock import AsyncMock, Mock

client = Mock(spec=HttpClient)
client.get.return_value = Response(status=200, body=b"ok")
...
client.get.assert_called_once_with("/health", timeout=5)
```

`spec=` prevents calls to methods that do not exist. Use `AsyncMock` for async
functions. Patch where the name is looked up, not where it is defined.

## Async tests

Pick one runner and be consistent:

```python
# pytest-asyncio
@pytest.mark.asyncio
async def test_fetch_uses_cache() -> None: ...

# anyio, if the project already uses it
@pytest.mark.anyio
async def test_fetch_uses_cache() -> None: ...
```

- Never call `asyncio.run()` inside a test.
- Bound every wait; use `asyncio.timeout` in the code under test.
- Use `anyio` or `pytest-asyncio` fixtures for event-loop-scoped resources.
- Test cancellation explicitly for long-running tasks.

## Property-based tests

Use Hypothesis for parsers, serializers, arithmetic, and invariants.

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_is_commutative(a: int, b: int) -> None:
    assert a + b == b + a

@given(st.text())
def test_encode_decode_roundtrip(value: str) -> None:
    assert decode(encode(value)) == value
```

Keep strategies valid but adversarial; add explicit examples for regressions
with `@example(...)`. Set a deadline and fail on too-slow inputs in CI.

## Determinism

- Inject a clock; never call `datetime.now()` in logic under test.
- Seed randomness; use `random.Random(seed)` or Hypothesis's control.
- Never sleep to synchronize tests; use events, polling with timeout, or fake
  time.
- Isolate the network. Integration tests use containers or recorded fixtures.
- Do not depend on filesystem order, locale, timezone, or hostname.
- Reset global state between tests; prefer no global state to reset.

## Coverage

- Enable branch coverage, not just line coverage.
- Treat coverage as a diagnostic, not a target. 100% coverage with weak
  assertions proves nothing.
- Enforce a floor on changed code, not a global number that encourages
  assertion-free tests.
- Exclude `TYPE_CHECKING`, `NotImplementedError`, and generated code explicitly.
- Review uncovered branches: each one is either dead code or a missing case.

## Flaky tests

1. Reproduce with `pytest --lf -x -vv` and a fixed seed.
2. Identify the source: time, randomness, network, shared state, ordering,
   concurrency, or a real race.
3. Fix the cause. Never add retries to hide nondeterminism.
4. If a test is inherently environmental, mark it and make the failure
   actionable.

## Anti-patterns

- Testing private functions because they are easier than the public behavior.
- Asserting on log strings, dict ordering, or exact error prose.
- Mocking the thing you are trying to test.
- One giant fixture that builds the whole application for every test.
- `time.sleep()` in tests.
- `assert result is not None` as the only assertion.
- Snapshot tests of huge outputs nobody reviews.
- Chasing coverage with tests that call code but never assert.

## Checklist

- [ ] Every bug fix has a regression test.
- [ ] Public behavior is covered at its boundary, including failures.
- [ ] Time, randomness, network, and filesystem are controlled.
- [ ] Integration tests use real adapters where practical.
- [ ] Mocks are limited to third-party boundaries and use `spec=`.
- [ ] Async tests use one configured runner and bounded waits.
- [ ] Slow/external tests are marked and run separately.
- [ ] The suite passes in random order and in parallel.
- [ ] Coverage highlights meaningful gaps, not a vanity number.

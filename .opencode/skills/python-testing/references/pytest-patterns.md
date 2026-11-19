# pytest patterns reference

## Testing exceptions precisely

```python
def test_parse_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match=r"invalid literal.*'abc'") as exc_info:
        parse_int("abc")
    assert exc_info.value.__cause__ is None
```

Use `match=` for stable parts of the message, never the whole sentence. Assert
the exception type the caller is expected to handle, not an internal one.

## Filesystem and paths

```python
def test_load_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('name = "demo"\n', encoding="utf-8")
    assert load_config(path).name == "demo"
```

Use `tmp_path`, not `tmpdir`. Never write into the repository during tests.

## Environment and monkeypatching

```python
def test_reads_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    assert settings().database_url.startswith("postgresql://")

def test_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HTTP_TIMEOUT", raising=False)
    assert settings().http_timeout == 5.0
```

`monkeypatch` restores automatically. For attributes:

```python
monkeypatch.setattr("package.module.now", lambda: FIXED_NOW)
```

## Capturing logs

```python
def test_retry_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="package.client"):
        client.fetch_with_retry()
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert "timeout" in caplog.text.lower()
```

Prefer asserting structured fields (`record.order_id`) over prose.

## Snapshots for serialized output

For large, stable output, use a reviewed snapshot:

```python
def test_render_invoice(snapshot) -> None:
    assert render(invoice) == snapshot
```

Keep snapshots small and commit them. Reject updates without review.

## Database integration tests

- Use a real database in a container or a temporary embedded instance.
- Run migrations from scratch once per session; truncate between tests.
- Wrap each test in a transaction and roll back where the stack supports it.
- Never share a database between parallel workers without unique schemas or
  databases per worker.
- Assert on committed state through a fresh session, not the same identity map.

```python
@pytest.fixture
def session(db_engine) -> Iterator[Session]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
```

## HTTP handlers

Prefer testing the real app with an in-process client:

```python
def test_create_user(client: TestClient) -> None:
    response = client.post("/users", json={"email": "a@example.com"})
    assert response.status_code == 201
    assert response.json()["email"] == "a@example.com"
```

Use dependency overrides for external services, not for the handler itself.
Assert status, content type, and a small part of the body. Do not assert on the
entire JSON unless the contract requires it.

## Time control

```python
class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta
```

Inject the clock into the code under test. For code you cannot change, freeze
time with `freezegun` or `time-machine`, and restrict it to that test.

## Parallel and random order

```sh
uv run pytest -n auto -p no:randomly
uv run pytest --randomly-seed=12345
```

Run the suite in random order and in parallel at least in CI. Failure under
either is a shared-state bug, not a reason to disable the plugin.

## Useful markers

```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
@pytest.mark.xfail(strict=True, reason="known bug #123")
```

`strict=True` makes an unexpected pass fail, which prevents stale xfails.

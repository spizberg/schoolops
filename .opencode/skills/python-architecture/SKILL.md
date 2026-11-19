---
name: Python Architecture
description: Design Python services and packages with clear boundaries, dependency injection, explicit errors, safe concurrency, configuration, and logging. Use when planning a feature, refactoring a module, or deciding between sync, threads, and async.
---

# Python Architecture

Good architecture makes the common change local. Optimize for deletion and
replacement of components, not for a diagram.

## Start from boundaries

Before writing classes, answer:

1. What enters and leaves the system? (HTTP, CLI, queue, file, DB)
2. What are the core rules that must hold regardless of I/O?
3. Which parts are expensive or impossible to change later? (schema, public API,
   storage format, auth model)
4. What has to be testable without a network, clock, or filesystem?

Then place code in layers with dependencies pointing inward:

```text
entrypoints (cli, http, workers)
        │
        ▼
application (use cases, orchestration, transactions)
        │
        ▼
domain (pure rules, value objects, entities)
        ▲
        │
adapters (db, http clients, queues, files)
```

- Domain imports no framework and performs no I/O.
- Application coordinates domain objects and ports.
- Adapters implement ports and translate external formats.
- Entrypoints parse input, call one use case, and format output.

A small script does not need four packages. Use the layers as a thinking tool,
not a mandatory directory tree. Introduce a module boundary when a real seam
appears, not preemptively.

## Dependency injection

Pass collaborators; do not construct or look them up inside business logic.

```python
class CreateOrder:
    def __init__(self, orders: OrderRepository, clock: Clock) -> None:
        self._orders = orders
        self._clock = clock

    def __call__(self, command: CreateOrderCommand) -> OrderId:
        order = Order.create(command.items, now=self._clock.now())
        self._orders.add(order)
        return order.id
```

- Depend on protocols, not concrete clients.
- Compose the graph once at startup (entrypoint or small container).
- Avoid a global service locator; it hides dependencies and breaks tests.
- Keep constructors free of I/O. Do work in an explicit `start()`/lifespan
  step so failures are observable.

## Errors

Use a small, intentional hierarchy for expected domain failures:

```python
class DomainError(Exception):
    """Base for expected business rule failures."""

class NotFound(DomainError): ...
class Conflict(DomainError): ...
class InvalidInput(DomainError): ...
```

Rules:

- Catch only what you can handle. Never `except Exception: pass`.
- Re-raise with context: `raise PaymentFailed(order_id) from exc`.
- Translate at the edge: domain error to HTTP status or CLI exit code.
- Do not use exceptions for normal control flow in hot loops.
- Fail fast on programmer errors (`assert` for invariants, `TypeError` for
  misuse); return errors or raise domain errors for expected outcomes.
- Never leak stack traces, SQL, or internal paths to untrusted callers.

## Concurrency decision table

| Workload | Use |
| --- | --- |
| Many network calls / sockets | `asyncio` |
| Blocking I/O with a sync library | Threads (`ThreadPoolExecutor`, `anyio.to_thread`) |
| CPU-bound Python | Processes (`ProcessPoolExecutor`) or a native library |
| CPU-bound, free-threaded build | Threads only after measurement; do not assume |
| Pipeline of independent tasks | `TaskGroup` (async) or executor (sync) |
| Periodic/background work | A real queue/worker, not `asyncio.create_task` in a web handler |

Async rules:

- Never call blocking I/O directly on the event loop. Offload it explicitly.
- Use `asyncio.TaskGroup` for structured concurrency; it cancels siblings on
  failure.
- Always bound waits with `asyncio.timeout()` or client timeouts.
- Let `CancelledError` propagate; clean up in `finally` or `aclose()`.
- Do not share a session/connection across tasks without checking client
  thread/task safety.
- Do not mix `asyncio.run()` into library code; let the application own the
  loop.

## Configuration

- Read configuration once at startup; validate it; then pass typed values.
- Precedence: explicit arguments > environment > config file > defaults.
- Use `pydantic-settings` or a dataclass parser for env vars.
- Never read `os.environ` deep inside domain code.
- Keep secrets out of defaults and out of logs.
- Validate cross-field constraints at startup so misconfiguration fails before
  traffic arrives.

## Logging and observability

- Use `logging.getLogger(__name__)`, never `print` in library code.
- Log events, not prose: `logger.info("order.created", extra={"order_id": ...})`.
- One log line per meaningful state change; include correlation IDs.
- Log at boundaries: request start/end, external call failures, retries.
- Never log credentials, tokens, full request bodies, or PII.
- Distinguish expected domain failures (info/warning) from bugs (exception).
- Add metrics for latency, error rate, queue depth, and saturation when the
  service runs in production.

## Resource management

- Use `with` for files, locks, transactions, and connections.
- Use `contextlib.ExitStack` for a dynamic set of resources.
- Close pools and clients in the application lifespan, not at import.
- Set timeouts on every network client; unbounded waits become outages.
- Avoid module-level mutable state and import-time side effects; they make
  tests order-dependent and workers unsafe.

## Design heuristics

- Rule of three: abstract after the third duplication, not the first.
- Composition over inheritance. Inherit for a genuine is-a contract only.
- Functions before classes; a class with one public method is usually a
  function.
- Keep functions small enough to name precisely.
- Make illegal states unrepresentable (enums, frozen dataclasses, validated
  models).
- Return new values instead of mutating shared structures.
- Depend on the smallest interface you need (`Readable`, `Callable`, a narrow
  protocol).
- If a test needs six mocks, the design has too many collaborators.

## Anti-patterns

- A `utils.py` that everything imports and nobody owns.
- Business rules inside HTTP handlers, ORM models, or Celery tasks.
- A god `Service` class that wraps every repository.
- Catching `Exception` at the top of every function.
- Async functions that secretly block.
- Global caches without eviction or invalidation.
- Framework types leaking into the domain.
- Premature microservices; a well-structured package is usually enough.

## Checklist

- [ ] Each module has one reason to change and an obvious owner.
- [ ] Domain code is testable with no I/O.
- [ ] Dependencies point inward; adapters implement ports.
- [ ] Dependencies are injected, not imported as singletons inside logic.
- [ ] Expected failures have a typed hierarchy and are translated at the edge.
- [ ] Concurrency model is explicit and blocking calls are offloaded.
- [ ] Config is validated at startup and passed as typed values.
- [ ] Logs are structured, contextual, and free of secrets.
- [ ] Resources have owners and are closed deterministically.
- [ ] No import-time side effects.

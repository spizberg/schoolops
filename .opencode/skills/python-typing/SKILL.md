---
name: Python Typing
description: Write precise, strict-mode Python type annotations using generics, protocols, TypedDict, overloads, and modern narrowing. Use when designing APIs, fixing type errors, or deciding how to model data.
---

# Python Typing

Types are executable design documentation. The goal is not zero red squiggles;
it is making invalid states unrepresentable and contracts obvious.

## Core principles

1. Type public boundaries: function signatures, class attributes, module
   constants, and data models. Private locals can be inferred.
2. Prefer precise types over `Any`. `Any` disables checking and spreads.
   - Truly arbitrary value: `object`, then narrow.
   - Arbitrary JSON: define a recursive `JsonValue` alias.
   - Unknown third-party: isolate behind a typed adapter.
3. Model data with the weakest tool that fits:
   - Small immutable record: `@dataclass(frozen=True, slots=True)` or
     `NamedTuple`.
   - Mapping with fixed keys: `TypedDict` (or a dataclass for behavior).
   - Closed set of values: `Literal` or `enum.StrEnum`.
   - Sum type: union of dataclasses plus `assert_never` exhaustiveness.
4. Accept the widest useful input (`Iterable`, `Mapping`, `Sequence`,
   `ReadableBuffer`); return the narrowest useful output (`list`, `dict`).
5. Annotate behavior, not implementation. If callers do not need a type
   parameter, do not expose it.

## Modern syntax (3.12+, no `from __future__` needed in 3.14)

```python
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Final, Literal, Protocol, Self, TypedDict, override

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]

class Config(TypedDict, total=False):
    host: str
    port: int

def connect(host: str, port: int = 5432, *, timeout: float | None = None) -> Connection: ...

def total(values: Iterable[int]) -> int:
    return sum(values)

class Repo(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def put(self, key: str, value: bytes) -> None: ...

def load(repo: Repo, key: str, default: bytes = b"") -> bytes:
    return repo.get(key) or default
```

- Use `X | None`, not `Optional[X]`.
- Use `list[str]`, `dict[str, int]`, not `List`/`Dict`.
- Use `collections.abc` for abstract containers.
- `Final` for constants, `ClassVar` for class-level state.
- `Self` for fluent/builder return types and alternative constructors.
- `@override` when overriding a base method; it catches rename drift.
- `@final` when subclassing would break invariants.

## Generics

```python
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

def first(items: Sequence[T]) -> T:
    if not items:
        raise ValueError("empty sequence")
    return items[0]

class Box[T]:                      # PEP 695 syntax, 3.12+
    def __init__(self, value: T) -> None:
        self.value = value
```

Use `ParamSpec` to preserve a wrapped callable's signature, and `Concatenate`
to add leading parameters:

```python
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def logged(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)
    return inner
```

Do not add a `TypeVar` used exactly once; it adds noise. Do not use a
`TypeVar` where `object` or a protocol states the real requirement.

## Protocols vs ABCs

| Use | When |
| --- | --- |
| `Protocol` | Structural contract at a seam; third-party types you cannot subclass; tests with fakes |
| `abc.ABC` | Shared implementation or enforced inheritance is genuinely wanted |
| Concrete base class | You control the hierarchy and reuse is real |

Prefer protocols for dependency injection. They keep the domain independent of
frameworks and make fakes trivial.

## Narrowing and exhaustiveness

```python
from typing import assert_never

def area(shape: Circle | Square) -> float:
    match shape:
        case Circle(radius=r):
            return math.pi * r**2
        case Square(side=s):
            return s**2
        case _:
            assert_never(shape)   # type checker proves this is unreachable
```

- Use `isinstance`, `match`, `in`, and truthiness to narrow.
- Prefer `TypeIs` (3.13+) over `TypeGuard` when a predicate narrows both
  branches; `TypeGuard` only narrows the positive branch.
- Avoid `cast` as a substitute for validation. When you must cast, put it next
  to the runtime check that justifies it.
- Never use a bare `# type: ignore`. Use `# type: ignore[code]  # reason` and
  prefer fixing or narrowing the ignore.

## Runtime boundaries

Static types do not validate untrusted input. At HTTP, CLI, file, and database
boundaries, parse into a model:

```python
from pydantic import BaseModel, Field

class CreateUser(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
    age: int = Field(ge=0, le=150)
```

Inside the process, trust the parsed model. Do not re-validate everywhere.
Keep domain models free of framework types where practical.

## Anti-patterns

- `dict[str, Any]` flowing through the core of the application.
- `-> None` on a function that returns a value, or missing return types on
  public functions.
- `Optional[T]` parameters that silently change behavior on `None`; use two
  functions or a default with a clear meaning.
- Boolean parameters that select behavior (`def render(html: bool)`); use an
  enum or separate functions.
- `list[str] | tuple[str, ...]` everywhere instead of `Sequence[str]`.
- Overloads with overlapping signatures that the implementation cannot
  distinguish.
- `type: ignore` cascades hiding a real modeling mistake.

## Checklist

- [ ] `mypy --strict` / pyright strict passes with a small, documented ignore
      list.
- [ ] No `Any` in public signatures without a comment justifying it.
- [ ] Data crossing an untrusted boundary is parsed and validated once.
- [ ] Every public function and method has parameter and return annotations.
- [ ] Unions are handled exhaustively (`assert_never` or explicit fallback).
- [ ] Protocols are used for seams; ABCs only when sharing implementation.
- [ ] Mutability is intentional: frozen dataclasses for values, `Final` for
      constants.

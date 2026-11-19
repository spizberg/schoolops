# Typing patterns reference

## JSON values

```python
type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
type JsonObject = dict[str, JsonValue]
```

Parse at the edge, then convert to domain models. Do not pass `JsonValue`
through business logic.

## Result types without exceptions everywhere

Exceptions are idiomatic in Python. Use a result type only where failure is an
expected, branchable outcome and the caller must handle it.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Ok[T]:
    value: T

@dataclass(frozen=True, slots=True)
class Err[E]:
    error: E

type Result[T, E] = Ok[T] | Err[E]

def parse(value: str) -> Result[int, str]:
    try:
        return Ok(int(value))
    except ValueError as exc:
        return Err(str(exc))

match parse("42"):
    case Ok(value):
        print(value)
    case Err(message):
        print(message)
```

## Generic repository protocol

```python
from collections.abc import Iterable
from typing import Protocol, TypeVar

T = TypeVar("T")
Id = TypeVar("Id")

class Repository[T, Id](Protocol):
    def get(self, id_: Id) -> T | None: ...
    def add(self, item: T) -> T: ...
    def all(self) -> Iterable[T]: ...
```

## Overloads for genuinely different return types

```python
from typing import Literal, overload

@overload
def read(path: str, *, binary: Literal[False] = False) -> str: ...
@overload
def read(path: str, *, binary: Literal[True]) -> bytes: ...
def read(path: str, *, binary: bool = False) -> str | bytes:
    data = Path(path).read_bytes()
    return data if binary else data.decode()
```

If callers always pass a literal, overloads are worth it. If they pass a
runtime-computed `bool`, simplify to a union return.

## Typed decorators

```python
from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def retry(times: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            last: Exception | None = None
            for _ in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # narrow this in real code
                    last = exc
            assert last is not None
            raise last
        return inner
    return decorate
```

## Discriminated unions

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class Card:
    kind: Literal["card"] = "card"
    number: str = ""

@dataclass(frozen=True, slots=True)
class Bank:
    kind: Literal["bank"] = "bank"
    iban: str = ""

type Payment = Card | Bank
```

Pydantic uses `Field(discriminator="kind")` for fast, precise parsing of the
same idea at the boundary.

## NewType for identifiers

```python
from typing import NewType

UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)
```

Prevents passing an order ID where a user ID is expected, at zero runtime cost.
Do not use `NewType` for values that need validation; validate when constructing.

## Common mypy fixes

| Error | Better fix |
| --- | --- |
| `Missing return statement` | Handle the path or mark the function `-> NoReturn` |
| `Incompatible types in assignment` | Narrow before assigning; do not cast blindly |
| `Need type annotation` | Annotate at initialization, not later |
| `Argument has incompatible type` | Widen the parameter or narrow the caller |
| `Cannot determine type of ...` | Annotate the attribute/class variable explicitly |
| Stub missing for library | Install `types-*`; otherwise a narrow module override |
| Recursive alias rejected | Use a string forward reference or a `Protocol` |

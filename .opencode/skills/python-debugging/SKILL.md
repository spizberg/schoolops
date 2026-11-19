---
name: Python Debugging
description: Diagnose Python defects systematically with reproduction, minimization, bisection, debuggers, tracing, and known failure-mode checks. Use when investigating a bug, crash, hang, incorrect result, or flaky failure.
---

# Python Debugging

Debugging is hypothesis-driven investigation, not random editing. Reproduce,
observe, narrow, fix, and prove the fix.

## Workflow

1. **State the symptom precisely.** Expected vs actual, inputs, environment,
   frequency, first occurrence. "It broke" is not a symptom.
2. **Reproduce it.** Prefer a failing test. If you cannot reproduce, you cannot
   know you fixed it. Record the exact command and data.
3. **Minimize.** Remove unrelated code, data, and configuration until the
   smallest case still fails. Minimization often reveals the cause.
4. **Form one hypothesis at a time.** Predict what you would observe if it were
   true, then test that prediction.
5. **Observe, don't guess.** Use a debugger, targeted logging, tracing, or
   `py-spy` rather than adding prints everywhere.
6. **Fix the cause, not the symptom.** Ask why the bad state was possible.
7. **Prove it.** Add a regression test that fails before and passes after.
8. **Check for siblings.** Search for the same pattern elsewhere.

## Reproduce

- Run the exact failing command in a clean environment.
- Capture versions: Python, OS, dependency lockfile, env vars (redacted).
- For intermittent bugs, loop the test with a fixed seed and record the seed
  that fails: `pytest --count=100 -x` (pytest-repeat) or a shell loop.
- For production-only bugs, reproduce with the real data shape and settings,
  or add temporary observability and roll it back.
- Never "fix" by restarting and moving on; the bug remains.

## Bisect

- Git: `git bisect start`, mark good/bad, let it find the commit. Automate with
  `git bisect run pytest path::test`.
- Data: binary search the input that triggers the failure.
- Dependencies: `uv lock --upgrade-package pkg` / pin versions to isolate.
- Code path: comment out or feature-flag halves of the path.

## Debuggers

```python
breakpoint()                  # uses pdb or PYTHONBREAKPOINT
```

Useful `pdb` commands: `l` (list), `n` (next), `s` (step), `c` (continue),
`p expr` (print), `pp expr` (pretty), `w` (where/stack), `u`/`d` (frame up/down),
`b file:line` (breakpoint), `!stmt` (execute), `q` (quit).

Better interactive options:

- `pdb` with `rich` or `pdb++` for colored source and sticky mode.
- IDE debuggers (VS Code `debugpy`, PyCharm) for breakpoints, watches, and
  conditional breakpoints.
- `python -m pdb script.py` to debug from the start.
- Post-mortem: `python -m pdb -c continue script.py`, then `p` the traceback
  frame after the crash.

Set `PYTHONBREAKPOINT=0` in production/tests to make `breakpoint()` a no-op.

## Observe without a debugger

- `logging.debug("state=%r", state)` temporarily; use `%r` to expose types and
  hidden characters.
- `traceback.print_stack()` to see how a path was reached.
- `sys.settrace` / `sys.monitoring` (3.12+) for targeted call tracing.
- `functools.wraps` and decorators can log inputs/outputs; keep it temporary.
- `faulthandler.enable()` dumps tracebacks on segfaults and can dump stacks on
  demand: `faulthandler.dump_traceback_later(30, repeat=True)`.
- For hangs: `py-spy dump --pid <pid>` shows every thread's stack.

## Isolate the layer

Ask which layer is wrong before reading code:

| Layer | Check |
| --- | --- |
| Input | Log the raw payload before parsing; validate it |
| Parsing | Round-trip the parsed model |
| Business logic | Call it directly with fixed inputs |
| Persistence | Inspect the actual stored rows |
| Serialization | Print the exact bytes sent/received |
| Transport | Compare client and server logs; check status codes |
| Environment | Compare config, versions, locale, timezone |

A surprising number of bugs are an encoding mismatch, a stale cache, a wrong
environment, or a type that is not what it looks like.

## Known Python traps

- **Mutable default argument**: `def f(x, acc=[])` shares `acc` across calls.
  Use `None` and create inside.
- **Late-binding closures**: lambdas in a loop capture the variable, not its
  value. Bind with a default argument or `functools.partial`.
- **Identity vs equality**: `is` compares identity; use `==` for values,
  `is None` for singletons.
- **Shallow copies**: `copy.copy` shares nested objects; use `deepcopy` or
  construct explicitly.
- **Integer/float**: `0.1 + 0.2 != 0.3`; use `Decimal` or `math.isclose`.
- **Truthiness**: `0`, `""`, `[]`, and `None` are falsy; distinguish "missing"
  from "empty".
- **Import cycles**: symptoms are partially initialized modules and
  `ImportError` for a name that exists. Move shared code or import locally.
- **Module shadowing**: a local file named `types.py`, `json.py`, or `logging.py`
  shadows the stdlib. Print `module.__file__`.
- **Exception swallowing**: `except Exception: pass` hides the cause. Use
  `raise ... from exc` and log with `exc_info=True`.
- **Encoding**: open files with an explicit `encoding="utf-8"`; decode bytes at
  the boundary.
- **Async not awaited**: a coroutine created but never awaited does nothing.
  Enable `-W error::RuntimeWarning`.
- **CancelledError**: in 3.8+ it derives from `BaseException`; `except
  Exception` will not catch it. Do not swallow it.
- **GIL/threads**: shared mutable state races; use locks or avoid sharing.
- **Iteration mutation**: mutating a list/dict while iterating causes skipped or
  repeated items; iterate over a copy.
- **`datetime.now()`**: naive and local; use timezone-aware UTC and inject a
  clock.
- **Regex greediness and catastrophic backtracking**: test with adversarial
  input; prefer anchored, simple patterns.

## When it is a hang or crash

- Hang: dump stacks (`py-spy dump`, `faulthandler`), check for deadlock, an
  unbounded wait, or a blocking call on the event loop.
- Segfault: run with `faulthandler`, check native extensions and versions,
  reproduce in isolation, try `PYTHONMALLOC=debug`.
- Memory growth: `tracemalloc` snapshots, then `memray`/`scalene`.
- Crash at shutdown: check non-daemon threads, atexit handlers, and async
  generator cleanup.

## Anti-patterns

- Changing code until the symptom disappears.
- Adding broad `try/except` to hide the failure.
- Debugging only on the production path with no observability.
- Assuming the bug is where the traceback points; the cause may be earlier.
- Leaving debug prints, `breakpoint()`, or verbose logging in the fix.
- Closing a bug without a regression test.

## Checklist

- [ ] Symptom, environment, and reproduction command are recorded.
- [ ] The failing case is minimized.
- [ ] The hypothesis was confirmed by observation, not intuition.
- [ ] The root cause is explained, not just the changed line.
- [ ] A regression test fails before the fix and passes after.
- [ ] Temporary debugging code is removed.
- [ ] The same failure mode was searched for elsewhere.
- [ ] If the bug reached production, a postmortem captures the detection gap.

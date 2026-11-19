---
name: Python Performance
description: Measure and fix Python performance problems with profiling, complexity analysis, caching, batching, concurrency, and memory reduction. Use when code is slow, memory-heavy, or before optimizing anything.
---

# Python Performance

Do not optimize what you have not measured. Premature optimization adds
complexity, risk, and bugs in exchange for speed nobody needed.

## Measure first

1. Define the goal in user terms: p95 latency, requests/sec, memory ceiling,
   startup time. "Faster" is not a target.
2. Reproduce with a realistic workload and dataset size.
3. Profile; find the actual hot path.
4. Change one thing. Re-measure with the same setup.
5. Keep the change only if the gain is real and the code stays maintainable.

| Question | Tool |
| --- | --- |
| Where does wall time go? | `py-spy record -o profile.svg -- python app.py` |
| Which functions are called how often? | `cProfile` + `pstats` / `snakeviz` |
| Which lines are hot? | `line_profiler` (`@profile`) |
| Is memory growing? | `tracemalloc`, `memray`, `scalene` |
| Is this snippet faster? | `timeit` / `pytest-benchmark` |
| Is the event loop blocked? | `asyncio.debug=True`, `py-spy` |
| CPU vs waiting? | `py-spy top`, `scalene` |

`py-spy` profiles production processes without restarting them. Use it before
adding instrumentation.

## Start with complexity

Most "Python is slow" problems are algorithmic or I/O-shaped.

| Smell | Fix |
| --- | --- |
| Nested loop over the same data | Build a dict/set index once |
| `x in list` in a loop | Use a `set` or `dict` |
| Repeated string concatenation | `"".join(parts)` |
| Re-computing inside a loop | Hoist or cache |
| Per-row database query | Batch query or join |
| Per-item network call | Batch API or bounded concurrency |
| Loading everything into memory | Stream/generator/chunk |
| Sorting inside a loop | Sort once |
| Re-parsing the same file per request | Parse once at startup |

Know the cost of common operations: list append O(1) amortized, dict lookup O(1)
average, `list.insert(0, x)` O(n), `sorted` O(n log n), `in list` O(n).

## Data structures and iteration

- Choose the container for the dominant operation, not for familiarity.
- Use `collections.Counter`, `defaultdict`, `deque`, `heapq`, `bisect` instead
  of hand-rolled loops.
- Prefer generators for large pipelines to bound memory.
- Use comprehensions for simple transforms; a generator expression avoids the
  intermediate list.
- `functools.lru_cache` / `cache` for pure, bounded, hashable inputs. Never
  cache results that depend on mutable external state without invalidation.
- `__slots__` (or `@dataclass(slots=True)`) for many small instances.

## Strings, bytes, and serialization

- Encode/decode at the boundary once; work in one representation internally.
- Use `bytes.join`, `bytearray`, and memoryviews for buffers; avoid repeated
  slicing copies.
- JSON is convenient, not always fast. For hot internal paths, consider
  `orjson`, `msgspec`, or a binary format, and measure.
- Avoid regex in tight loops; compile once (`re.compile`) and prefer literal
  string methods when possible.

## I/O and concurrency

- Batch and pipeline I/O. The fastest network call is the one you avoid.
- Reuse connections and clients; creating a client per request is expensive.
- Add bounded concurrency for independent I/O: `asyncio.TaskGroup` with a
  semaphore, or a thread pool for blocking libraries.
- Never use unbounded `gather` over untrusted input; it exhausts memory and
  overwhelms peers.
- CPU-bound Python does not get faster with threads on a standard build. Use
  processes, native extensions, or vectorization.
- Python 3.14 free-threaded builds change the calculus, but only after
  measurement. Check that the whole dependency stack supports it.

## Memory

- Find retained objects with `tracemalloc` snapshots before and after the
  operation.
- Watch for caches without a size limit, global registries, and closures that
  capture large frames.
- Stream files and query results (`fetchmany`, `iter_lines`) instead of
  materializing.
- Use `array`, `numpy`, or `memoryview` for numeric bulk data.
- Delete large temporaries and avoid keeping references in tracebacks/logs.
- Set a memory ceiling and test it; memory leaks are outages.

## Benchmarking correctly

- Warm up (imports, JIT-less Python caches, connection pools).
- Run enough repetitions; report median and spread, not a single run.
- Use realistic data sizes and distributions.
- Compare like for like on the same machine and load.
- Isolate: no debugger, no coverage, no dev server reloader.
- Keep a benchmark in the repo for paths that matter; run it in CI only when
  stable enough to avoid noise.

```python
# pytest-benchmark
def test_parse_benchmark(benchmark) -> None:
    result = benchmark(parse_document, SAMPLE)
    assert result is not None
```

## Optimization order

1. Remove work (cache, batch, avoid redundant calls).
2. Choose a better algorithm or data structure.
3. Reduce allocations and copies.
4. Move I/O off the hot path (background, precompute).
5. Add concurrency for independent waits.
6. Use a native/vectorized library.
7. Rewrite in another language only when the above are exhausted and the
   boundary is clean.

Readability is a feature. A 10% gain that makes the code unmaintainable is
usually a loss. Require a measured, documented reason for clever code.

## Anti-patterns

- Optimizing without a profile.
- Benchmarking with toy data.
- Caching with no invalidation or bound.
- Fire-and-forget tasks to "make it faster".
- Using threads for CPU-bound work on the GIL build.
- Micro-optimizing cold paths.
- Adding a dependency for a 2% gain.
- Holding a lock across I/O or `await`.
- Assuming an async rewrite fixes a slow query.

## Checklist

- [ ] A concrete performance target exists.
- [ ] A profile identifies the bottleneck.
- [ ] The fix addresses the measured cause, not a guess.
- [ ] Results are compared with the same workload and environment.
- [ ] Caches are bounded and invalidated correctly.
- [ ] Concurrency is bounded and cancellation-safe.
- [ ] Memory behavior is measured for large inputs.
- [ ] A benchmark or regression test guards the hot path.
- [ ] The optimized code is still readable and tested.

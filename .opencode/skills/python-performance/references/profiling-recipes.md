# Profiling recipes

## Quick timing

```python
import timeit

timeit.timeit("parse(s)", globals={"parse": parse, "s": SAMPLE}, number=10_000)
```

Or from the shell:

```sh
uv run python -m timeit -s "from pkg import parse; s = open('sample').read()" "parse(s)"
```

Never time with `time.time()` around a single call; noise dominates.

## cProfile

```sh
uv run python -m cProfile -o out.prof -m package
uv run python -c "import pstats; pstats.Stats('out.prof').sort_stats('cumtime').print_stats(30)"
```

Use `cumtime` to find expensive call trees, `tottime` to find functions that
spend time in their own body. Filter with `pstats.Stats(...).print_stats('pkg')`.

Programmatic:

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
run_workload()
profiler.disable()
pstats.Stats(profiler).sort_stats("cumulative").print_stats(20)
```

`cProfile` adds overhead and misses C-level time attribution. For production,
use `py-spy`.

## py-spy

```sh
py-spy top --pid 12345
py-spy record --pid 12345 --duration 30 --output profile.svg
py-spy dump --pid 12345          # current stack of every thread
```

- `record` samples stacks and produces a flame graph; wide = hot.
- `dump` answers "what is it stuck on right now?"
- Works on running production processes without code changes.

## Line profiling

```python
# pip install line_profiler
@profile
def hot_function(rows):
    ...
```

```sh
kernprof -l -v script.py
```

Only add `@profile` temporarily; it is not a pytest builtin.

## Memory: tracemalloc

```python
import tracemalloc

tracemalloc.start()
run_workload()
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics("lineno")[:10]:
    print(stat)
```

Compare two points:

```python
before = tracemalloc.take_snapshot()
run_workload()
after = tracemalloc.take_snapshot()
for stat in after.compare_to(before, "lineno")[:10]:
    print(stat)
```

For native allocations and retention graphs, use `memray` or `scalene`.

## Bytes at rest

```python
import sys

sys.getsizeof(obj)              # shallow only
sum(sys.getsizeof(x) for x in items)   # still misses nested objects
```

Use `pympler.asizeof` or `tracemalloc` for real totals.

## Async event-loop blocking

```python
import asyncio

async def main() -> None:
    loop = asyncio.get_running_loop()
    loop.set_debug(True)        # warns when callbacks exceed the threshold
    loop.slow_callback_duration = 0.05
    await run()
```

If a coroutine blocks, `py-spy dump` shows whether it is in a C call or a
blocking syscall. Offload with `asyncio.to_thread`.

## SQL and N+1

- Log query counts per request; a request with 200 queries is a design bug.
- Use `EXPLAIN ANALYZE` on the real schema and data volume.
- Check for missing indexes on filter/join columns.
- Batch inserts with `executemany` or a bulk API.
- Avoid `SELECT *` and loading full result sets for pagination.

## Load testing

- Drive the real entrypoint, not internal functions.
- Model realistic request mix, payload sizes, and think time.
- Measure p50/p95/p99 and error rate; averages hide tail latency.
- Watch CPU, memory, connections, and queue depth alongside latency.
- Test at 1x, 2x, and 5x expected traffic to find the knee.

Tools: `locust`, `k6`, `wrk`, `vegeta`.

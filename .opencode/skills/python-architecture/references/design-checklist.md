# Architecture review checklist

Use this when designing a feature or reviewing a module boundary. Answer each
question with evidence from the code, not intention.

## Boundaries

- What are the inputs? Are they parsed and validated exactly once?
- What are the outputs? Are they serialized in one place?
- Can the core logic run without a database, network, clock, or filesystem?
- Which modules import which? Draw the graph. Are there cycles?
- Does any domain module import a framework, ORM, or HTTP client?
- Is there a single place where transactions begin and commit?

## Data model

- Are identifiers distinct types or at least named clearly?
- Are optional fields truly optional, or does `None` overload meanings?
- Can an invalid combination be constructed? If yes, where is it prevented?
- Is mutation controlled? Are shared values copied or frozen?
- Does the storage schema match the domain, or does it leak into it?
- Are units, time zones, and currency explicit?

## Failure behavior

- List every external call. What is its timeout, retry policy, and failure mode?
- What happens when the database is unavailable for one second? One minute?
- Are retries safe (idempotent)? Is there a deduplication key?
- Are partial failures possible? Is there a transaction or compensation?
- Does the caller see a useful, non-leaking error?
- Are expected errors distinguishable from bugs in logs and metrics?

## Concurrency

- Which functions are async? Do any of them block?
- Is shared mutable state accessed from more than one thread/task?
- Are locks held across `await` or I/O? (Usually a bug.)
- Are tasks awaited or cancelled? Any fire-and-forget calls?
- Is shutdown graceful? Are in-flight requests drained?
- Are connection pools sized for the worker count?

## Configuration and operations

- Can the service start with an invalid config? Why not?
- Are secrets provided by the environment or secret manager?
- Is there a health check that reflects dependencies?
- Can the service be deployed without downtime?
- Are logs sufficient to reconstruct a failed request?
- Is there a metric that would reveal this feature failing silently?

## Change safety

- What is the migration path for existing data or clients?
- Is the change backward compatible during a rolling deploy?
- Can the feature be disabled without a redeploy?
- What is the rollback plan?
- Which tests would fail if this behavior regressed?

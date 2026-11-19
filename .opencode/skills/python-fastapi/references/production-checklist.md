# FastAPI production checklist

Review before the first deploy and after any change to serving, auth, or data.

## Runtime

- [ ] `fastapi run`/Uvicorn with explicit workers; no `--reload` in production.
- [ ] One process per CPU (or measured); worker count matches DB pool budget.
- [ ] `--proxy-headers` and `--forwarded-allow-ips` configured for the actual
      proxy; client IP and scheme are correct.
- [ ] Graceful shutdown drains in-flight requests before exit.
- [ ] Engine, HTTP clients, and pools are disposed in lifespan.
- [ ] Server and proxy timeouts are finite and longer than the slowest
      legitimate request.
- [ ] Request body limits enforced at the proxy and in upload handlers.
- [ ] Keep-alive settings match the proxy/load balancer.

## Configuration

- [ ] Settings are validated at startup; missing required values fail fast.
- [ ] Environment name drives docs, debug, and log verbosity.
- [ ] Secrets come from the environment or secret manager, not files in the
      image.
- [ ] `/docs` and `/openapi.json` are protected or disabled in public production
      if the API is private.
- [ ] No development defaults (test JWT secret, permissive CORS) reach
      production.
- [ ] Config changes are deployable without code changes.

## HTTP and API contract

- [ ] `/v1` prefix and a versioning/deprecation policy exist.
- [ ] OpenAPI is generated in CI; breaking changes require a version bump.
- [ ] Every endpoint declares request/response models and error responses.
- [ ] Validation errors, auth errors, domain errors, and 500s share one
      Problem Details shape.
- [ ] Status codes match semantics (201 create, 204 delete, 409 conflict).
- [ ] Pagination is capped; large lists use keyset cursors.
- [ ] PATCH distinguishes absent fields from explicit `null`.
- [ ] Unsafe retryable operations support `Idempotency-Key` where needed.
- [ ] CORS uses explicit origins; wildcard is never combined with credentials.
- [ ] `TrustedHostMiddleware` is configured when host headers matter.
- [ ] `Location`, `ETag`, `Cache-Control`, and `Retry-After` are correct where
      used.

## Security

- [ ] TLS terminates at a trusted proxy; redirects and secure cookies are set.
- [ ] JWTs verify signature, algorithm allowlist, `exp`, `iat`, `iss`, `aud`.
- [ ] HS256 secrets are at least 32 random bytes; asymmetric keys are rotated.
- [ ] Tokens are never accepted from query strings or logged.
- [ ] Object-level authorization is enforced in the query or service.
- [ ] Password hashing uses Argon2id/scrypt; login is rate-limited.
- [ ] Input is validated by Pydantic; SQL is parameterized; shell is avoided.
- [ ] Uploads enforce type/size limits, use generated names, and are stored
      outside the web root.
- [ ] CORS, CSP, HSTS, and frame options are set at the edge.
- [ ] Dependency scanning and lockfile installs run in CI.
- [ ] Secrets and PII are redacted from logs, traces, and error responses.
- [ ] See the `python-security` skill for the full checklist.

## Data

- [ ] Migrations run as a separate deploy step, not in app startup.
- [ ] Migrations are backward compatible for rolling deploys.
- [ ] Every migration has a tested rollback or a documented forward-fix.
- [ ] Transactions have explicit boundaries; repositories do not commit.
- [ ] Pool size × worker count stays below the database connection limit.
- [ ] Queries are indexed for their filters and sort order.
- [ ] N+1 queries are absent; relationships load explicitly.
- [ ] Timeouts and statement limits are set on the database and driver.
- [ ] Backups and restore procedures are tested.
- [ ] Destructive changes require confirmation, audit logging, and a retention
      policy.

## Observability

- [ ] Structured JSON logs include timestamp, level, service, request ID, route
      template, status, and duration.
- [ ] No bodies, tokens, passwords, cookies, or PII in logs.
- [ ] Traces propagate through HTTP, DB, and queue calls (OpenTelemetry).
- [ ] Metrics cover request rate, errors, duration (RED), pool saturation, and
      queue depth.
- [ ] Alerts exist for error rate, p95 latency, saturation, and dependency
      failures.
- [ ] `/health/live` checks the process; `/health/ready` checks critical
      dependencies and is cached.
- [ ] Health endpoints are unauthenticated but expose no internal details.
- [ ] A deploy is identifiable in logs/metrics (version or commit SHA).

## Failure behavior

- [ ] Outbound calls have connect/read timeouts and bounded retries with
      jitter.
- [ ] Retries are limited to idempotent operations or protected by idempotency
      keys.
- [ ] Circuit breaking or load shedding exists for critical dependencies.
- [ ] Background tasks that must survive a crash use a queue, not
      `BackgroundTasks`.
- [ ] The outbox publisher is idempotent and monitored.
- [ ] 5xx responses are generic; details are in logs with a correlation ID.
- [ ] Rate limits return 429 with `Retry-After`.
- [ ] The service degrades predictably when the DB or a dependency is down.

## Deploy and rollback

- [ ] Image runs as a non-root user with a read-only filesystem where possible.
- [ ] Image contains no dev dependencies, tests, `.env`, or build caches.
- [ ] Startup fails fast on invalid config; readiness gates traffic.
- [ ] Rolling deploy is safe for the schema and API version in flight.
- [ ] Rollback is one action and has been rehearsed.
- [ ] Feature flags or config can disable risky behavior without a redeploy.
- [ ] Post-deploy smoke test covers auth, one read, one write, and health.
- [ ] On-call runbook lists dashboards, logs, common failures, and escalation.

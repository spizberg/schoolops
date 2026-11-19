# Security review checklist

Use for any change that touches input parsing, auth, files, subprocesses,
network calls, secrets, or dependencies. Mark each item pass, fail, or N/A with
a one-line justification.

## Input and output

- [ ] Every entrypoint validates input against a schema, not ad hoc checks.
- [ ] Maximum sizes are enforced before buffering (body, file, field count).
- [ ] Unknown fields are rejected or explicitly ignored by policy.
- [ ] Output is encoded for its context (HTML, JSON, URL, shell).
- [ ] Error responses do not reveal internals.
- [ ] Pagination and query parameters have upper bounds.

## Authentication and authorization

- [ ] Authentication is required where expected; anonymous access is explicit.
- [ ] Authorization checks the specific object or action, not only the route.
- [ ] Tenant/user scoping is applied in the query, not after fetching.
- [ ] Tokens are validated (signature, algorithm, expiry, issuer, audience).
- [ ] Session cookies use `Secure`, `HttpOnly`, and an appropriate `SameSite`.
- [ ] Password reset and invite tokens are single-use and expire.
- [ ] Login and sensitive endpoints are rate-limited.

## Data and storage

- [ ] Sensitive columns are encrypted or tokenized where required.
- [ ] Passwords are hashed with Argon2id or scrypt and a per-user salt.
- [ ] PII has a retention policy and is deleted when no longer needed.
- [ ] Database constraints enforce invariants, not just application code.
- [ ] Backups are encrypted and access-controlled.
- [ ] Test data is synthetic or properly anonymized.

## Files

- [ ] Upload names are generated server-side.
- [ ] Resolved paths stay inside the intended base directory.
- [ ] Symlinks are handled or rejected.
- [ ] Archive extraction checks each entry for traversal and size.
- [ ] Temporary files are created securely and cleaned up.
- [ ] File permissions are least-privilege.

## Processes and code

- [ ] `subprocess` uses an argument list and `shell=False`.
- [ ] No untrusted data reaches `eval`, `exec`, `compile`, or `pickle`.
- [ ] No `yaml.load` without a safe loader.
- [ ] XML parsing disables external entities.
- [ ] Deserialized data is validated into a typed model.

## Network

- [ ] Outbound calls set connect and read timeouts.
- [ ] Response sizes are bounded.
- [ ] TLS verification is enabled.
- [ ] User-supplied URLs are allowlisted and private address ranges blocked.
- [ ] Redirects are bounded and revalidated.
- [ ] Webhooks are authenticated (signature or shared secret).

## Secrets and logging

- [ ] No secret in code, tests, fixtures, or committed config.
- [ ] Secrets are injected at runtime and scoped narrowly.
- [ ] Logs redact tokens, passwords, cookies, and PII.
- [ ] Debug mode and verbose tracebacks are off in production.
- [ ] A leaked secret would be detectable and rotatable.

## Dependencies and CI

- [ ] Lockfile is committed and used in production installs.
- [ ] New dependencies are justified and reviewed.
- [ ] A vulnerability scan runs in CI.
- [ ] CI actions are pinned and run with least privilege.
- [ ] Build artifacts do not include dev secrets or `.env` files.

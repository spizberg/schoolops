---
name: Python Security
description: Harden Python code against injection, unsafe deserialization, path traversal, SSRF, secret leaks, and dependency risk. Use when handling untrusted input, subprocesses, files, credentials, auth, or third-party packages.
---

# Python Security

Security work is about trust boundaries and failure modes, not a checklist at
the end. Assume every external input is hostile and every secret eventually
leaks unless you prevent it.

## Trust boundaries

Identify what crosses each boundary and validate it exactly once:

| Boundary | Untrusted input | Control |
| --- | --- | --- |
| HTTP | Path, query, headers, body, cookies | Schema validation, size limits, authn/authz |
| CLI | Arguments, env vars, files | Explicit parsing, no shell interpolation |
| Database | Stored values from other writers | Parameterized queries, constraints |
| Files | Names, contents, archives | Path containment, size/format limits |
| Network clients | Responses | Timeouts, size limits, schema checks |
| Queue | Message payloads | Schema, idempotency, signature |

Validate positively: allow known shapes and reject everything else. Do not
blacklist characters; encoding makes blacklists bypassable.

## Injection

### SQL

```python
# Good: parameterized
cursor.execute("SELECT id FROM users WHERE email = %s", (email,))

# Bad: interpolation
cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
```

Identifiers (table/column names) cannot be parameterized. Map user input through
an allowlist to constants; never interpolate it.

### Shell

```python
import subprocess

# Good: argument list, no shell
subprocess.run(["git", "log", "--oneline", "-n", "5"], check=True, shell=False)

# Bad: shell=True with interpolated input
subprocess.run(f"git log {user_input}", shell=True)
```

If a shell is truly required, quote with `shlex.quote` and still pass a list.
Prefer library APIs over shelling out.

### Templates and HTML

- Use auto-escaping templates (Jinja2 with `autoescape=True`, Django templates).
- Do not mark user data `safe`/`Markup`.
- Set a Content Security Policy at the edge; escape for the context (HTML, JS,
  URL, CSS) rather than one generic escape.
- For rich text, sanitize with a maintained allowlist library, never regex.

### Code execution

Never pass user input to `eval`, `exec`, `compile`, `__import__`, or
`pickle.loads`. There is no safe sandbox for arbitrary Python. If you need
configurable logic, use a constrained DSL with its own parser.

## Deserialization

| Format | Safe default |
| --- | --- |
| JSON | `json.loads`; size-limit the payload |
| TOML/YAML | `tomllib`; `yaml.safe_load` (never `yaml.load` without `SafeLoader`) |
| Pickle | Do not accept from untrusted sources; it executes code |
| `marshal` | Not safe for untrusted data |
| XML | Disable entities/external DTDs; prefer JSON |
| CSV | Limit rows/fields; beware formula injection when re-exporting |

Validate the parsed structure into a typed model before use. Parsing is not
validation.

## Files and paths

```python
from pathlib import Path

BASE = Path("/srv/uploads").resolve()

def safe_path(user_name: str) -> Path:
    candidate = (BASE / user_name).resolve()
    if not candidate.is_relative_to(BASE):
        raise ValueError("path escapes base directory")
    return candidate
```

- Reject absolute paths and `..` from untrusted input, then verify containment
  after resolution (symlinks included).
- Generate server-side names for uploads; do not trust the client filename.
- Enforce size, count, and type limits before reading everything into memory.
- Create temp files with `tempfile`, not predictable names in shared dirs.
- Set restrictive permissions for secrets and uploaded data.
- Guard archive extraction against zip-slip and decompression bombs.

## Secrets

- Load from the environment or a secret manager; never commit them.
- `.env` is for local development and must be gitignored.
- Never log secrets, tokens, passwords, cookies, or auth headers. Add redaction
  at the logging layer.
- Use `secrets.token_urlsafe()` / `secrets.compare_digest()`, not `random`.
- Keep secrets out of exception messages, crash reports, and URLs.
- Rotate on exposure; assume a leaked credential is compromised.
- Limit scope and lifetime of tokens; prefer short-lived credentials.

## Passwords and cryptography

- Hash passwords with Argon2id (`argon2-cffi`) or `hashlib.scrypt`; never
  SHA-256 alone, never a homemade scheme.
- Use a unique salt per password (handled by the library).
- Compare digests with `hmac.compare_digest`.
- Use `cryptography` for encryption; do not implement primitives.
- Encrypt in transit (TLS, verify certificates) and at rest where required.
- Do not invent token formats or sign your own JWTs; use a maintained library
  and verify `alg`, `exp`, `iss`, and `aud`.

## Web and network

- Enforce authentication and authorization on every entrypoint, deny by
  default. A UI hiding a button is not authorization.
- Check object ownership on every read/write (IDOR), not just role.
- Set request body, header, and upload size limits.
- Add timeouts and response size limits to every outbound client.
- For user-supplied URLs (SSRF): allowlist schemes/hosts, resolve DNS, block
  private/link-local/metadata ranges, and re-check after redirects.
- Do not follow redirects blindly with credentials attached.
- Set secure cookie flags (`Secure`, `HttpOnly`, `SameSite`).
- Apply rate limits and account lockout to auth endpoints.

## Dependencies and supply chain

- Commit a lockfile; install with `--frozen`/`--require-hashes` in production.
- Minimize dependencies and review new ones (maintenance, license, popularity,
  transitive count).
- Run `pip-audit` or `uv audit` in CI; fail on known critical vulnerabilities.
- Pin CI actions by commit SHA, not a floating tag.
- Do not run install scripts from untrusted packages in privileged environments.
- Generate an SBOM if the project ships to customers.

## Logging and errors

- Return generic errors to users; log details internally with a correlation ID.
- Do not include stack traces, SQL, file paths, or dependency versions in
  responses.
- Redact sensitive fields by key and by pattern; test the redaction.
- Treat logs as sensitive data: access-controlled and retained deliberately.

## Checklist

- [ ] Every external input is validated into a typed model at the boundary.
- [ ] Queries are parameterized; identifiers come from an allowlist.
- [ ] No `shell=True`, `eval`, `exec`, or unsafe pickle on untrusted data.
- [ ] YAML/XML/archive parsing uses safe loaders and limits.
- [ ] File paths are resolved and checked for containment.
- [ ] Secrets come from the environment/manager and are never logged.
- [ ] Passwords use Argon2id/scrypt; comparisons are constant-time.
- [ ] Authz is enforced server-side per object, not just per route.
- [ ] Outbound calls have timeouts, size limits, and SSRF protections.
- [ ] Dependencies are locked and audited in CI.
- [ ] Errors are generic externally and detailed internally.
- [ ] Sensitive-data redaction is tested.

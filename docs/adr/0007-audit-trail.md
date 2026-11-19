# ADR-0007: Append-only application audit log

- **Status:** Accepted
- **Date:** 2026-11-20

## Context

The system stores personal data about minors and their guardians. Changes to children,
households, guardians, attendance, enrollments, classes, sessions, and volunteers need to
be attributable to an administrator and need to show what changed. The audit trail must be
simple to operate and must not become a second source of truth for current data.

## Decision

- Add an append-only `audit_logs` table:
  - `actor_user_id` (nullable, `ON DELETE SET NULL`)
  - `action` (`create`, `update`, `delete`, `generate`)
  - `entity_type` and `entity_id`
  - `changes` as JSONB snapshots/diffs
  - `created_at` only; no `updated_at`
- Record audit entries explicitly inside the same transaction as the mutation, so a
  mutation cannot commit without its audit row.
- Store `{ "after": ... }` for creates, `{ "before": ... }` for deletes, and
  `{ "changes": { field: { "from", "to" } } }` for updates. Attendance submissions store a
  per-child before/after map and visitor before/after lists.
- Load the actor from the authenticated admin request and attach it to the database
  session; system/CLI actions may have no actor.
- Expose a read-only filtered query API and screen. There is no update or delete endpoint.
- Audit rows are not included in domain reports.

## Consequences

- Every mutation has an attributable record without changing service signatures.
- The audit table grows with write volume; indexes support entity and date queries, and a
  retention/archive policy can be added later.
- The audit log is application-level and can be altered by a database superuser. A future
  compliance requirement may ship entries to append-only external storage.
- Read access is admin-only; the log contains personal data and must follow the same
  privacy rules as the underlying records.

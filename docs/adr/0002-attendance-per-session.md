# ADR-0002: Attendance is per class session, gated by a ministry calendar

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

The children's ministry records attendance for age-band classes that meet on Sundays. A
single weekly headcount would lose class-level history and make lesson content and
volunteer participation hard to attach to a specific meeting.

## Decision

- Model `class_sessions` (class, date, start/end, topic, lesson content) as the unit of
  attendance and lesson content.
- Model meeting days explicitly: ministry year + configured weekdays (Sunday by default)
  + no-class days.
- Attendance records are unique per `(class_session_id, child_id)`.
- Child status is `present` or `absent`; a missing record is `not recorded`.
- One-off visitors are recorded by name on the session and are excluded from the enrolled
  roster.
- Volunteers serving a session are recorded in a separate session volunteer list, not as
  child attendance.
- Daily or service-level attendance is an aggregation, not a separate table.

## Consequences

- Supports class and child reporting, lesson content, and volunteer participation with one
  session model.
- More data entry than a single weekly headcount; mitigated by bulk roster upsert and
  session generation.
- Multiple services on one Sunday are separate sessions, not a schema change.
- Calendar rules are data, so church closures need no code change.
- A future check-in/check-out feature can reference sessions without replacing attendance.

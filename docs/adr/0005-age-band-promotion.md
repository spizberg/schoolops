# ADR-0005: Reviewed source→target mapping for annual promotion

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

Classes are recreated each ministry year and children move up by age band. Automatic
age-based assignment is ambiguous because a church may run several classes for the same age
band, and families may have pastoral reasons for a particular placement. Class names do
not persist across years.

## Decision

- Promotion is a two-step workflow: **preview** then **apply**.
- The administrator maps each source-year class to one target-year class.
- The preview lists assignments, unmatched children, and children already enrolled in the
  target year, with each child's age at the target year start and both age bands.
- Apply creates target-year enrollments from the reviewed mapping, starting at the target
  year start date.
- Apply is idempotent and skips children already actively enrolled in the target year.
- Unmatched children are enrolled manually; they are never silently dropped.

## Consequences

- The director stays in control of pastoral and age-band exceptions.
- A bad mapping is visible before any enrollment is created.
- Promotion is an explicit annual task rather than an automatic background process.
- A future rules engine could suggest mappings, but the reviewed apply step remains.

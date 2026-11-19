# ADR-0006: Secure check-in/check-out is out of scope for the MVP

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

Children's ministries often need secure drop-off and pickup: name labels, matching pickup
codes, authorized pickup people, and a record of who collected each child. That is a
different workflow from attendance and adds significant safety, printing, and verification
requirements.

## Decision

- The MVP records attendance only (`present`/`absent` per child, plus named visitors).
- There are no name labels, pickup codes, pickup verification, or authorized-pickup lists.
- The data model keeps attendance attached to sessions so a future check-in record can be
  added as a separate table without rewriting attendance.
- The limitation is stated in the requirements and UI.

## Consequences

- The MVP stays focused on rosters, attendance, lesson content, and family contactability.
- The church continues its existing check-in process outside the app.
- Adding check-in later is additive: a `check_ins` table can reference sessions and
  children, while attendance remains the ministry record.
- A future check-in feature will need its own safeguarding and privacy review.

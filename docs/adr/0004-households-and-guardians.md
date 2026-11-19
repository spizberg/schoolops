# ADR-0004: Household grouping and per-child guardian links

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

Siblings usually share the same parents and address. Storing guardian details separately
on each child duplicates records, causes inconsistent phone numbers, and makes searching
for a family unreliable. Some families are split across households, and grandparents or
other caregivers may be authorized contacts for a child in a different household.

## Decision

- Add a `households` table (optional name, address, notes).
- Add a `guardians` table. A guardian may belong to a household, but the link is optional.
- A child may belong to a household, but the link is optional for edge cases.
- Link guardians to children through `child_guardians` with `relationship`, `is_primary`,
  and `is_emergency`.
- Enforce at most one primary guardian per child with a partial unique index.
- A guardian can be linked to several children, and a child can have guardians from more
  than one household.
- Activating a child without a guardian warns but does not block.

## Consequences

- Guardian and household details are entered once and shared across siblings.
- A primary guardian is explicit per child, so separated or blended families can be
  represented without duplicating a "family" record.
- Deleting or merging households needs care; a merge workflow can be added later.
- Reports and rosters can show guardian contact details without joining through a
  child-scoped contacts table.

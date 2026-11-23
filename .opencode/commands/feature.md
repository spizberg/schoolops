---
description: Start the full-stack SDLC pipeline (spec → design → API/UI → tests → review) with human gates.
agent: orchestrator
---

Start the SDLC pipeline for the following feature:

$ARGUMENTS

Follow your orchestrator workflow exactly:

1. Determine scope: full-stack (default), `backend-only`/`API-only`, or
   `frontend-only`/`UI-only`. State it in the gate 1 summary.
2. Delegate the spec to `spec` (derive a kebab-case slug if none given).
3. Stop at GATE 1 and ask the user to approve the spec.
4. After approval, delegate the design to `architect`, including the frozen API contract
   and the Angular route/component/state plan.
5. Stop at GATE 2 and ask the user to approve the design and contract freeze.
6. After approval, run `backend` then `frontend` (parallel only under your parallelism
   rules), then `test` and `web-test` in parallel, then `reviewer`.
7. Loop on findings (max 3), routing each to its owner.
8. Stop at GATE 3 and ask the user to approve the commit.

Do not skip gates and do not edit files yourself.

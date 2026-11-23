---
description: Review the current full-stack changes read-only, run the quality gate, and return a verdict.
agent: reviewer
subagent: false
---

Review the current working tree and any commits on this branch that are not on `main`.
Cover the FastAPI backend and the Angular frontend, including contract drift between
`docs/02-design.md`, the Pydantic schemas, and `frontend/src/app/core/models.ts`.

Extra focus for this review: $ARGUMENTS

Follow your reviewer process: determine the change set, read the relevant spec and design
sections, review file by file, run `just check`, and return findings in severity order
followed by a single verdict (APPROVE / REQUEST_CHANGES / BLOCKED). Do not edit anything.

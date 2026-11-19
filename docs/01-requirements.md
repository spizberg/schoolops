# Children's Bible Study Group — Requirements (MVP)

- **Status:** Accepted — church design
- **Version:** 2.0
- **Date:** 2026-11-19

## 1. Vision

Replace the spreadsheets and paper registers used by the Children's Bible Study Group,
a single-congregation children's ministry. The system gives the ministry director one authenticated place to maintain
ministry years, age-band classes, households and guardians, children, volunteers, weekly
Sunday sessions, lesson content, and attendance — including one-off visitors — and to see
which children have not been seen recently.

The application is not a school administration system. It does not manage grades,
transcripts, tuition, or check-in/check-out security.

## 2. Goals and success measures

| Goal | Measure |
| --- | --- |
| Replace manual registers | Register a volunteer, a household with two children, an age-band class, and record a Sunday of attendance in under 15 minutes |
| Trustworthy attendance | Attendance is rejected for non-meeting days and children who are neither enrolled nor marked as visitors; one record per child per session |
| Family contactability | Every active child is linked to a household with at least one reachable guardian |
| Attendance visibility | The director can see weekly rosters, attendance history, and children not seen in a chosen period |
| Safe handling of minors' data | No unauthenticated access, every mutation audited, no PII in logs; check-in and pickup verification are explicitly out of scope |
| Single source of truth | Rosters, households, sessions, and attendance live in one system instead of spreadsheets |

## 3. Scope

### In scope (MVP)

- Ministry years, meeting weekdays (Sunday by default), no-class days (holidays/closures)
- Volunteers, including one lead volunteer per class for planning
- Households, guardians, children, and guardian links per child
- Age-band classes, enrollments with history, and an annual promotion workflow
- Class sessions with per-session lesson content and resource links
- Multiple volunteers recorded as serving a session
- Attendance for enrolled children (`present`/`absent`) and one-off visitor entries
- Reports: weekly roster, attendance history, "not seen recently", dashboard, CSV export
- Admin authentication, role-ready authorization, audit trail

### Out of scope (explicit non-goals, later phases)

- Secure check-in/check-out, name labels, pickup codes, or pickup verification
- Authorized pickup lists and custody restrictions
- Volunteer background checks, safeguarding training, or compliance expiry tracking
- Parent/child portal, volunteer self-service accounts
- Email/SMS messaging to guardians (we store contacts, we do not message them)
- Multi-campus or multi-church tenancy
- Grades, report cards, transcripts, tuition, or any finance features
- Native mobile apps, file/document uploads
- Curriculum series/units or reusable lesson libraries
- Public API for third parties

## 4. Personas

| Persona | Needs | MVP access |
| --- | --- | --- |
| **Ministry director / administrator** | Run all operations, correct mistakes, monitor attendance | Full access |
| **Class leader** (phase 2) | Record attendance, volunteers, and content for own classes | Own classes only |
| **Parent/guardian** (later) | See a child's attendance and update contacts | Read-only, own children |
| **Check-in volunteer** (later, only if check-in is added) | Find a child and record drop-off/pickup | Check-in screens only |

## 5. Glossary

| Term | Meaning |
| --- | --- |
| **Ministry year** | A named period (e.g. `2026-2027`) with start/end dates and configured meeting weekdays |
| **Meeting day** | A date inside the ministry year whose weekday is configured and which is not a no-class day |
| **No-class day** | Holiday, church closure, or other date on which classes do not meet |
| **Household** | A family grouping used to share an address and connect siblings and guardians |
| **Guardian** | An adult contact for a child (parent, grandparent, other caregiver) |
| **Child** | A minor in the ministry; status is active, inactive, visitor, or left |
| **Volunteer** | An adult serving in the ministry; one is the class lead, and several may serve a session |
| **Class** | A named age-band group within a ministry year (e.g. `Preschool`, `K–2`) |
| **Age band** | The age range a class serves, stored as a label plus optional minimum/maximum age |
| **Enrollment** | The dated association of a child to a class; historical records are kept |
| **Promotion** | Creating next-year enrollments from a reviewed source-class → target-class mapping |
| **Class session** | One meeting of a class on a date with start/end times; the unit for attendance, volunteers, and lesson content |
| **Attendance record** | A child's `present`/`absent` status for one session, or a named one-off visitor entry |
| **Visitor** | A child attending once without a regular enrollment; recorded by name, not on the roster |

## 6. Functional requirements

Each requirement is written as a user story with acceptance criteria (AC).

### FR-01 — Ministry years and calendar

*As an administrator, I can define a ministry year and its calendar so that attendance is
only recorded on real meeting days.*

- AC1: I can create a year with a unique label, start date, end date, and meeting weekdays
  (default Sunday).
- AC2: Start date must be strictly before end date.
- AC3: At most one year is active at a time; activating a year deactivates the previous one.
- AC4: I can add no-class days (date, name, kind: holiday/closure/other) within the year.
- AC5: A no-class day cannot fall outside the year or duplicate an existing one.
- AC6: The system can list all meeting days in a date range, excluding non-configured
  weekdays and no-class days.
- AC7: Classes are scoped to a ministry year.
- AC8: The default meeting weekday is Sunday; the value remains configurable per year.

### FR-02 — Volunteers

*As an administrator, I can maintain the team of volunteers who serve children.*

- AC1: Create/edit/deactivate a volunteer with first name, last name, phone (required),
  email (optional), and join date (optional).
- AC2: If an email is provided it must be unique (case-insensitive); phone is required.
- AC3: A deactivated volunteer cannot be assigned as a new class lead or session volunteer
  but remains on historical classes and sessions.
- AC4: I can search volunteers by name/phone/email and see the classes they lead and the
  sessions they served.
- AC5: Each class has at most one lead volunteer for planning and organization.
- AC6: Any active volunteer may be recorded as serving any session; a session can have
  multiple volunteers.

### FR-03 — Households and guardians

*As an administrator, I can keep family and guardian details so every child is reachable.*

- AC1: Create/edit a household with an optional name (e.g. `The Hopper family`), address,
  and notes.
- AC2: Create/edit a guardian with first name, last name, phone (required), optional email,
  optional household link, and notes.
- AC3: Link a guardian to a child with a relationship and `primary`/`emergency` flags.
- AC4: At most one guardian per child is primary; promoting a new primary clears the old one.
- AC5: A guardian may be linked to multiple children, and siblings may share a household.
  A guardian may be linked to a child in another household (e.g. separated parents or
  grandparents).
- AC6: Guardians are searchable by name/phone/email; a child's profile shows all linked
  guardians and the household.
- AC7: Activating a child without a guardian is allowed but warns; it does not block data
  entry or migration.
- AC8: Guardian and link changes are audit-logged.

### FR-04 — Children

*As an administrator, I can maintain child records with the safety information needed on a
Sunday.*

- AC1: Create/edit a child with first name, last name, date of birth (required), optional
  grade, optional household, allergies, medical notes, photo consent, join date, status
  (`active`, `inactive`, `visitor`, `left`), and notes.
- AC2: There is no admission number. Names are not unique.
- AC3: I can search and filter children by name, household, class, and status.
- AC4: A child profile shows household, guardians, enrollment history, attendance summary,
  allergies, medical notes, and photo consent.
- AC5: Deactivating or archiving a child does not delete historical attendance.
- AC6: Allergies and medical notes are visible on the session roster where attendance is
  recorded.
- AC7: Photo consent is stored as `granted`, `denied`, or `not_recorded`.

### FR-05 — Classes, age bands, enrollments, and promotion

*As an administrator, I can create age-band classes, enroll children, and promote them to
the next year's classes.*

- AC1: Create/edit a class with name, ministry year, age-band label, optional minimum and
  maximum age, lead volunteer, room, optional capacity (informational), and curriculum
  overview.
- AC2: Class name is unique within a ministry year; if minimum/maximum ages are present,
  minimum must not exceed maximum.
- AC3: A class belongs to exactly one ministry year; its sessions must fall inside it.
- AC4: Capacity is informational and never blocks enrollment.
- AC5: I can enroll a child with a start date and optional end date.
- AC6: A child has at most one active class per ministry year.
- AC7: The class roster shows only enrollments active on the requested date (default today).
- AC8: Removing an enrollment ends it (sets an end date); it does not delete attendance.
- AC9: I can promote children from a source year to a target year by mapping each source
  class to a target class, previewing the assignments, unmatched children, and children
  already enrolled, then applying the reviewed mapping.
- AC10: Promotion is idempotent: re-applying the same mapping does not create duplicate
  active enrollments.
- AC11: A class with enrollment or session history cannot be deleted; an empty class may be
  removed.

### FR-06 — Sessions, volunteers, and lesson content

*As an administrator, I can schedule each class's Sunday session, record which volunteers
served, and write what was taught.*

- AC1: Create/edit a session with date, start time, end time, topic (optional), notes
  (optional), lesson content in Markdown (optional), and resources (optional list of
  label/URL links).
- AC2: Session date must be a meeting day in the class's ministry year.
- AC3: Start time must be before end time.
- AC4: A class cannot have two sessions with the same date and start time.
- AC5: I can generate sessions in bulk for a date range, skipping non-meeting days, no-class
  days, and existing sessions at the same start time.
- AC6: Lesson content and resources are optional, so a session can be scheduled before
  content is written.
- AC7: I can record one or more active volunteers as serving a session; the same volunteer
  cannot be recorded twice for one session.
- AC8: The class curriculum overview remains editable on the class; per-session content is
  stored on the session.
- AC9: A class may have multiple sessions on the same Sunday if the church runs multiple
  services; each is a separate session with its own start time.

### FR-07 — Attendance

*As an administrator, I can record attendance for enrolled children and one-off visitors,
and report attendance.*

- AC1: For a session I can mark each enrolled child as `present` or `absent`, with an
  optional note.
- AC2: Attendance can only be recorded for children enrolled in the class on the session
  date, unless the entry is a one-off visitor.
- AC3: A one-off visitor can be recorded by name without enrollment; visitor entries are
  clearly marked and never appear on the regular roster.
- AC4: There is at most one attendance record per child per session; re-submitting updates
  the existing record.
- AC5: Attendance cannot be recorded on a date that is no longer a meeting day; this is
  re-checked on write.
- AC6: I can record attendance for the whole roster in one request (bulk upsert).
- AC7: Attendance rate = `present` / total recorded records for the period. Missing records
  are `not recorded` and never counted as absence.
- AC8: Visitor counts are reported separately and are not mixed into enrolled-child rates.
- AC9: I can view attendance by child or class for a date range, with counts and rate.
- AC10: Changes to attendance are audit-logged with actor, timestamp, and previous value.
- AC11: Volunteer participation is recorded on the session volunteer list, separate from
  child attendance.

### FR-08 — Reports and dashboard

- AC1: Dashboard shows the active ministry year, counts of active children/volunteers/classes,
  today's sessions, attendance recorded today, and a count of children not seen recently.
- AC2: The weekly roster for a class and date includes guardian contact, allergies, medical
  notes, and photo consent indicators needed for that session.
- AC3: Reports are filterable by date range.
- AC4: I can report children not seen since a chosen date, optionally filtered by class,
  showing last present date and missed sessions.
- AC5: I can export a per-child attendance summary as a server-generated CSV for a date
  range, filtered by class and/or child.
- AC6: Reports never require more than 3 seconds for one ministry year of data at the target
  scale.

### FR-09 — Authentication, authorization, audit

- AC1: All API resources except health checks and login require authentication.
- AC2: An admin account is created via a CLI command; passwords are hashed with Argon2id
  and never logged or returned.
- AC3: Login returns a short-lived JWT access token (8 hours for the pilot); invalid or
  expired tokens get `401`.
- AC4: A `role` field with values `admin`, `leader`, `parent` exists from day one; only
  `admin` is granted access in the MVP.
- AC5: Every create/update/delete on children, guardians, attendance, and other personal
  data writes an audit record (actor, action, entity type/id, timestamp, changed fields).
- AC6: Login attempts are rate-limited (application-level for MVP; gateway in production).

## 7. Business rules

| ID | Rule |
| --- | --- |
| BR-01 | A meeting day is a configured weekday inside the ministry year that is not a no-class day |
| BR-02 | A session exists only on a meeting day |
| BR-03 | Attendance exists only for a class session; each child has at most one record per session |
| BR-04 | A one-off visitor is recorded by name and is never part of the regular roster |
| BR-05 | A child has at most one active class per ministry year |
| BR-06 | A child has at most one primary guardian |
| BR-07 | Historical records are never hard-deleted when a person is deactivated; classes with history are protected |
| BR-08 | The active ministry year is the default context for new classes and reports |
| BR-09 | Class capacity is informational and never blocks enrollment |
| BR-10 | Check-in, checkout, labels, and pickup verification are not part of the MVP |
| BR-11 | Class age bands guide grouping and promotion, but promotion requires a reviewed mapping |

## 8. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | **Security:** OWASP ASVS level 1; Argon2id passwords; JWT signature/expiry validated; authorization checked server-side on every object access |
| NFR-02 | **Privacy:** children's and guardians' data is personal data about minors — collect only what is listed here; allergies/medical notes are sensitive; no PII in logs; support export/delete workflow before production data is loaded |
| NFR-03 | **Performance:** p95 < 300 ms for paginated list endpoints and < 3 s for year-level reports at 1,000 children / 200 sessions per class |
| NFR-04 | **Accessibility:** WCAG 2.2 AA for all screens; keyboard-operable forms and tables |
| NFR-05 | **Reliability:** daily automated PostgreSQL backups; restore tested each release |
| NFR-06 | **i18n:** English UI first; all strings externalized so French can be added without code changes |
| NFR-07 | **Observability:** structured JSON logs with request ID and latency; health endpoints; error tracking |
| NFR-08 | **Compatibility:** latest two versions of Chrome, Firefox, Safari, Edge |
| NFR-09 | **Data integrity:** schema constraints + service validation; all schema changes via migrations |

## 9. Data classification

| Class | Data | Handling |
| --- | --- | --- |
| Restricted | Children's names, date of birth, allergies, medical notes, photo consent | Admin-only; encrypted in transit; audited access; never in logs |
| Confidential | Guardian names, phone, email, address; household address | Admin-only; encrypted in transit; audited access |
| Internal | Volunteer contact details, class/roster data, attendance | Authenticated staff only |
| Public | App name, help text | None |

## 10. Assumptions

| # | Assumption | Proposed default |
| --- | --- | --- |
| A1 | Congregation | One congregation and one site for the MVP |
| A2 | Meeting pattern | Sunday only; multiple sessions per Sunday are allowed if services differ |
| A3 | Classes | Age-band classes, recreated each ministry year; one active class per child per year |
| A4 | Promotion | **Confirmed:** reviewed source-class → target-class mapping with preview; not automatic |
| A5 | Check-in | No check-in/check-out, labels, or pickup verification in the MVP |
| A6 | Volunteers | Phone required, email optional; one class lead, many session volunteers; no compliance tracking |
| A7 | Attendance | `present`/`absent` only; missing means "not recorded"; volunteers are tracked by session participation |
| A8 | Visitors | One-off visitor attendance by name, without enrollment |
| A9 | Guardians | **Confirmed:** one primary guardian per child; guardians may be shared across siblings and link across households |
| A10 | Existing data | No spreadsheet import required for the MVP; generate demo/seed data only |
| A11 | Retention | Keep attendance history; add export/delete workflow before production data is loaded |
| A12 | Time zone | Stored as dates/times local to the church; server stores UTC timestamps for audit fields |

## 11. Delivery slices

The church-domain refactor, audit trail, and hardening baseline have landed. Remaining
work is seed/demo data and deployment.

| Slice | Contents | Depends on |
| --- | --- | --- |
| 0 | Foundation: repo, CI, DB, health checks, walking skeleton | — |
| 1 | Ministry domain refactor: years/calendar, volunteers, households/guardians, children, classes, enrollments | 0 |
| 2 | Sessions, session volunteers, attendance, reports | 1 |
| 3 | Promotion workflow | 1 |
| 4 | Dashboard, not-seen report, CSV exports | 2 |
| 5 | Audit trail | 1 |
| 6 | Hardening, seed data, deployment | all |

> Slices 1–5 and the hardening baseline are implemented. No production data has been
> loaded; seed/demo data and deployment remain.

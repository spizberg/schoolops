"""Deterministic demo data for local testing."""

from dataclasses import dataclass
from datetime import date, time, timedelta
from random import Random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.db.models import (
    AttendanceRecord,
    Child,
    ChildGuardian,
    ClassGroup,
    ClassSession,
    Enrollment,
    Guardian,
    Household,
    MinistryYear,
    NoClassDay,
    SessionVolunteer,
    Volunteer,
)
from schoolops.domain.enums import (
    AttendanceStatus,
    ChildStatus,
    NoClassDayKind,
    PhotoConsent,
    VolunteerStatus,
)


class DemoDataExistsError(Exception):
    """Raised when the database already contains ministry years."""


@dataclass(frozen=True)
class SeedResult:
    ministry_years: int
    volunteers: int
    households: int
    guardians: int
    children: int
    classes: int
    enrollments: int
    sessions: int
    session_volunteers: int
    attendance: int
    visitors: int


VOLUNTEERS: tuple[tuple[str, str, str, str | None], ...] = (
    ("Sarah", "Mitchell", "+33 6 10 00 00 01", "sarah.mitchell@example.com"),
    ("David", "Okafor", "+33 6 10 00 00 02", None),
    ("Emily", "Chen", "+33 6 10 00 00 03", "emily.chen@example.com"),
    ("Michael", "Brown", "+33 6 10 00 00 04", None),
    ("Rachel", "Kim", "+33 6 10 00 00 05", "rachel.kim@example.com"),
    ("James", "Taylor", "+33 6 10 00 00 06", None),
    ("Naomi", "Johnson", "+33 6 10 00 00 07", "naomi.johnson@example.com"),
    ("Peter", "Martin", "+33 6 10 00 00 08", None),
    ("Laura", "Garcia", "+33 6 10 00 00 09", "laura.garcia@example.com"),
    ("Daniel", "Smith", "+33 6 10 00 00 10", None),
    ("Hannah", "Wilson", "+33 6 10 00 00 11", "hannah.wilson@example.com"),
    ("Samuel", "Davis", "+33 6 10 00 00 12", None),
)

# (first, last, date of birth, current class, allergies, medical notes, photo consent)
CURRENT_CHILDREN: tuple[tuple[str, str, str, str, str | None, str | None, PhotoConsent], ...] = (
    ("Chloe", "Mitchell", "2022-04-12", "Nursery", "Strawberries", None, PhotoConsent.GRANTED),
    ("Noah", "Mitchell", "2019-02-05", "Kindergarten", None, None, PhotoConsent.GRANTED),
    (
        "Ethan",
        "Okafor",
        "2021-09-15",
        "Preschool",
        "Peanuts",
        "Carries an EpiPen",
        PhotoConsent.GRANTED,
    ),
    ("Zara", "Okafor", "2018-07-21", "Primary", None, "Mild asthma", PhotoConsent.GRANTED),
    ("Lily", "Chen", "2020-03-30", "Kindergarten", None, None, PhotoConsent.DENIED),
    ("Oliver", "Brown", "2023-01-25", "Nursery", None, None, PhotoConsent.GRANTED),
    (
        "Ava",
        "Brown",
        "2017-11-02",
        "Primary",
        "Bee stings",
        "Allergy plan on file",
        PhotoConsent.GRANTED,
    ),
    ("Mia", "Kim", "2022-06-18", "Preschool", None, None, PhotoConsent.NOT_RECORDED),
    ("Jack", "Taylor", "2020-05-14", "Kindergarten", None, None, PhotoConsent.GRANTED),
    ("Sophie", "Taylor", "2016-12-03", "Primary", None, None, PhotoConsent.GRANTED),
    ("Elijah", "Johnson", "2021-07-09", "Preschool", "Dairy", None, PhotoConsent.GRANTED),
    ("Grace", "Martin", "2019-04-22", "Kindergarten", None, None, PhotoConsent.NOT_RECORDED),
    ("Leo", "Martin", "2023-02-11", "Nursery", None, None, PhotoConsent.GRANTED),
    ("Sofia", "Garcia", "2018-10-17", "Primary", None, None, PhotoConsent.GRANTED),
    ("Benjamin", "Wilson", "2021-01-28", "Kindergarten", None, None, PhotoConsent.DENIED),
    ("Caleb", "Davis", "2021-11-05", "Preschool", None, None, PhotoConsent.GRANTED),
    ("Ruby", "Davis", "2017-08-19", "Primary", None, None, PhotoConsent.GRANTED),
    ("Eva", "Nguyen", "2018-12-09", "Primary", None, None, PhotoConsent.NOT_RECORDED),
)

# (first, last, date of birth, past class)
PROMOTABLE_CHILDREN: tuple[tuple[str, str, str, str], ...] = (
    ("Ella", "Clarke", "2020-02-10", "Preschool"),
    ("Samuel", "Clarke", "2018-05-20", "Primary"),
    ("Amelia", "Reed", "2021-01-15", "Preschool"),
    ("Isaac", "Reed", "2019-09-10", "Primary"),
    ("Maya", "Patel", "2020-06-05", "Preschool"),
    ("Jonah", "Patel", "2019-03-18", "Primary"),
)

# Household name → (guardians, current children)
# Guardian: (first, last, phone, email, relationship, is_emergency)
HOUSEHOLDS: tuple[
    tuple[str, str, tuple[tuple[str, str, str, str | None, str, bool], ...], tuple[str, ...]],
    ...,
] = (
    (
        "The Mitchell family",
        "8 Church Lane",
        (
            (
                "Sarah",
                "Mitchell",
                "+33 6 20 00 00 01",
                "sarah.mitchell@example.com",
                "Mother",
                True,
            ),
            ("Paul", "Mitchell", "+33 6 20 00 00 02", None, "Father", False),
        ),
        ("Chloe", "Mitchell", "Noah", "Mitchell"),
    ),
    (
        "The Okafor family",
        "14 Elm Road",
        (
            ("David", "Okafor", "+33 6 20 00 00 03", "david.okafor@example.com", "Father", True),
            ("Amara", "Okafor", "+33 6 20 00 00 04", None, "Mother", False),
        ),
        ("Ethan", "Okafor", "Zara", "Okafor"),
    ),
    (
        "The Chen family",
        "21 Oak Street",
        (
            ("Emily", "Chen", "+33 6 20 00 00 05", "emily.chen@example.com", "Mother", True),
            ("Wei", "Chen", "+33 6 20 00 00 06", None, "Father", False),
        ),
        ("Lily", "Chen"),
    ),
    (
        "The Brown family",
        "3 Maple Close",
        (
            ("Michael", "Brown", "+33 6 20 00 00 07", "michael.brown@example.com", "Father", True),
            ("Claire", "Brown", "+33 6 20 00 00 08", None, "Mother", False),
        ),
        ("Oliver", "Brown", "Ava", "Brown"),
    ),
    (
        "The Kim family",
        "42 Station Road",
        (("Rachel", "Kim", "+33 6 20 00 00 09", "rachel.kim@example.com", "Mother", True),),
        ("Mia", "Kim"),
    ),
    (
        "The Taylor family",
        "5 Orchard Way",
        (
            ("James", "Taylor", "+33 6 20 00 00 10", "james.taylor@example.com", "Father", True),
            ("Anna", "Taylor", "+33 6 20 00 00 11", None, "Mother", False),
        ),
        ("Jack", "Taylor", "Sophie", "Taylor"),
    ),
    (
        "The Johnson family",
        "17 Cedar Avenue",
        (("Naomi", "Johnson", "+33 6 20 00 00 12", "naomi.johnson@example.com", "Mother", True),),
        ("Elijah", "Johnson"),
    ),
    (
        "The Martin family",
        "9 Willow Drive",
        (
            ("Peter", "Martin", "+33 6 20 00 00 13", "peter.martin@example.com", "Father", True),
            ("Ruth", "Martin", "+33 6 20 00 00 14", None, "Mother", False),
        ),
        ("Grace", "Martin", "Leo", "Martin"),
    ),
    (
        "The Garcia family",
        "30 Hillcrest Road",
        (("Laura", "Garcia", "+33 6 20 00 00 15", "laura.garcia@example.com", "Mother", True),),
        ("Sofia", "Garcia"),
    ),
    (
        "The Wilson family",
        "11 Brook Lane",
        (("Hannah", "Wilson", "+33 6 20 00 00 16", "hannah.wilson@example.com", "Mother", True),),
        ("Benjamin", "Wilson"),
    ),
    (
        "The Davis family",
        "2 Meadow View",
        (
            ("Samuel", "Davis", "+33 6 20 00 00 17", "samuel.davis@example.com", "Father", True),
            ("Rebecca", "Davis", "+33 6 20 00 00 18", None, "Mother", False),
        ),
        ("Caleb", "Davis", "Ruby", "Davis"),
    ),
    (
        "The Nguyen family",
        "6 Rose Court",
        (("Linh", "Nguyen", "+33 6 20 00 00 19", "linh.nguyen@example.com", "Mother", True),),
        ("Eva", "Nguyen"),
    ),
    (
        "The Clarke family",
        "23 High Street",
        (
            (
                "Margaret",
                "Clarke",
                "+33 6 20 00 00 20",
                "margaret.clarke@example.com",
                "Mother",
                True,
            ),
            ("Andrew", "Clarke", "+33 6 20 00 00 21", None, "Father", False),
        ),
        (),
    ),
    (
        "The Reed family",
        "4 Victoria Road",
        (
            ("Thomas", "Reed", "+33 6 20 00 00 22", "thomas.reed@example.com", "Father", True),
            ("Helen", "Reed", "+33 6 20 00 00 23", None, "Mother", False),
            ("Margaret", "Reed", "+33 6 20 00 00 24", None, "Grandmother", True),
        ),
        (),
    ),
    (
        "The Patel family",
        "18 Kingsway",
        (
            ("Priya", "Patel", "+33 6 20 00 00 25", "priya.patel@example.com", "Mother", True),
            ("Amit", "Patel", "+33 6 20 00 00 26", None, "Father", False),
        ),
        (),
    ),
)

PAST_CLASSES: tuple[tuple[str, str, int, int, str, str], ...] = (
    ("Toddlers", "1-2 years", 1, 2, "Room A", "Nursery rhymes and simple Bible stories."),
    ("Preschool", "3-5 years", 3, 5, "Room B", "Old Testament stories and crafts."),
    ("Primary", "6-9 years", 6, 9, "Room C", "Gospel of Mark and memory verses."),
)

CURRENT_CLASSES: tuple[tuple[str, str, int, int, str, str], ...] = (
    ("Nursery", "2-3 years", 2, 3, "Room A", "God made me and loves me."),
    ("Preschool", "4-5 years", 4, 5, "Room B", "Creation through Joseph."),
    ("Kindergarten", "6-7 years", 6, 7, "Room C", "Moses, David, and the prophets."),
    ("Primary", "8-10 years", 8, 10, "Room D", "The life of Jesus and the early church."),
)

PAST_FOR_CURRENT = {
    "Nursery": "Toddlers",
    "Preschool": "Preschool",
    "Kindergarten": "Preschool",
    "Primary": "Primary",
}

TOPICS = (
    "Creation",
    "Noah and the Ark",
    "Abraham's Promise",
    "Moses and the Exodus",
    "David and Goliath",
    "Daniel in the Lions' Den",
    "Jonah and the Big Fish",
    "The Good Shepherd",
    "The Birth of Jesus",
    "The Wise Men",
    "Jesus Calms the Storm",
)

CLASS_LEADS = {
    "Nursery": "Sarah Mitchell",
    "Preschool": "David Okafor",
    "Kindergarten": "Emily Chen",
    "Primary": "Michael Brown",
    "Toddlers": "Rachel Kim",
    "Primary (past)": "Naomi Johnson",
}

SESSIONS = tuple(
    day
    for day in (date(2026, 9, 6) + timedelta(days=7 * index) for index in range(12))
    if day != date(2026, 10, 11)
)


async def seed_demo(session: AsyncSession) -> SeedResult:
    """Create a complete demo year, raising if ministry years already exist."""
    existing = await session.scalar(select(func.count()).select_from(MinistryYear))
    if existing:
        raise DemoDataExistsError(
            "The database already contains ministry years. Demo seeding was skipped."
        )

    current_year = MinistryYear(
        label="2026-2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 6, 30),
        meeting_weekdays=[7],
        is_active=True,
    )
    past_year = MinistryYear(
        label="2025-2026",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 30),
        meeting_weekdays=[7],
        is_active=False,
    )
    session.add_all([current_year, past_year])
    await session.flush()

    session.add_all(
        [
            NoClassDay(
                ministry_year_id=current_year.id,
                date=date(2026, 10, 11),
                name="Church picnic",
                kind=NoClassDayKind.OTHER,
            ),
            NoClassDay(
                ministry_year_id=current_year.id,
                date=date(2026, 12, 27),
                name="Christmas break",
                kind=NoClassDayKind.HOLIDAY,
            ),
            NoClassDay(
                ministry_year_id=current_year.id,
                date=date(2027, 4, 4),
                name="Easter break",
                kind=NoClassDayKind.HOLIDAY,
            ),
            NoClassDay(
                ministry_year_id=past_year.id,
                date=date(2025, 12, 28),
                name="Christmas break",
                kind=NoClassDayKind.HOLIDAY,
            ),
        ]
    )

    volunteers = [
        Volunteer(
            first_name=first,
            last_name=last,
            phone=phone,
            email=email,
            joined_on=date(2024, 9, 1),
            status=VolunteerStatus.ACTIVE,
        )
        for first, last, phone, email in VOLUNTEERS
    ]
    volunteers[-1].status = VolunteerStatus.INACTIVE
    session.add_all(volunteers)
    await session.flush()
    volunteer_by_name = {f"{item.first_name} {item.last_name}": item for item in volunteers}

    households = [Household(name=name, address=address) for name, address, _, _ in HOUSEHOLDS]
    session.add_all(households)
    await session.flush()
    household_by_name = {item.name: item for item in households if item.name is not None}

    guardian_by_key: dict[tuple[str, str], Guardian] = {}
    guardians: list[Guardian] = []
    children: list[Child] = []
    child_by_name: dict[tuple[str, str], Child] = {}
    child_current_class: dict[tuple[str, str], str] = {}
    child_past_class: dict[tuple[str, str], str] = {}

    for name, _, guardian_rows, _child_keys in HOUSEHOLDS:
        household = household_by_name[name]
        for first, last, phone, email, _, _ in guardian_rows:
            guardian = Guardian(
                household_id=household.id,
                first_name=first,
                last_name=last,
                phone=phone,
                email=email,
            )
            guardians.append(guardian)
            guardian_by_key[(first, last)] = guardian
    session.add_all(guardians)
    await session.flush()

    for first, last, dob, class_name, allergies, medical, photo in CURRENT_CHILDREN:
        child = Child(
            first_name=first,
            last_name=last,
            date_of_birth=date.fromisoformat(dob),
            grade=class_name,
            allergies=allergies,
            medical_notes=medical,
            photo_consent=photo,
            status=ChildStatus.ACTIVE,
            joined_on=date(2025, 9, 1),
        )
        children.append(child)
        child_by_name[(first, last)] = child
        child_current_class[(first, last)] = class_name
        child_past_class[(first, last)] = PAST_FOR_CURRENT[class_name]

    # Attach current children to their households.
    for name, _, _, child_keys in HOUSEHOLDS:
        household = household_by_name[name]
        for index in range(0, len(child_keys), 2):
            first, last = child_keys[index], child_keys[index + 1]
            child = child_by_name[(first, last)]
            child.household_id = household.id

    for first, last, dob, past_class in PROMOTABLE_CHILDREN:
        child = Child(
            first_name=first,
            last_name=last,
            date_of_birth=date.fromisoformat(dob),
            status=ChildStatus.ACTIVE,
            joined_on=date(2025, 9, 1),
            photo_consent=PhotoConsent.GRANTED,
        )
        children.append(child)
        child_by_name[(first, last)] = child
        child_past_class[(first, last)] = past_class

    # Attach promotable children to their households.
    promotable_household = {
        ("Ella", "Clarke"): "The Clarke family",
        ("Samuel", "Clarke"): "The Clarke family",
        ("Amelia", "Reed"): "The Reed family",
        ("Isaac", "Reed"): "The Reed family",
        ("Maya", "Patel"): "The Patel family",
        ("Jonah", "Patel"): "The Patel family",
    }
    for key, household_name in promotable_household.items():
        child_by_name[key].household_id = household_by_name[household_name].id

    session.add_all(children)
    await session.flush()

    # Guardian links: each household guardian is linked to its household children.
    for _, _, guardian_rows, child_keys in HOUSEHOLDS:
        for child_index in range(0, len(child_keys), 2):
            child = child_by_name[(child_keys[child_index], child_keys[child_index + 1])]
            for index, (first, last, _, _, relationship, emergency) in enumerate(guardian_rows):
                session.add(
                    ChildGuardian(
                        child_id=child.id,
                        guardian_id=guardian_by_key[(first, last)].id,
                        relationship=relationship,
                        is_primary=index == 0,
                        is_emergency=emergency,
                    )
                )
    for child_key, household_name in promotable_household.items():
        _, _, guardian_rows, _ = next(row for row in HOUSEHOLDS if row[0] == household_name)
        child = child_by_name[child_key]
        for index, (first, last, _, _, relationship, emergency) in enumerate(guardian_rows):
            session.add(
                ChildGuardian(
                    child_id=child.id,
                    guardian_id=guardian_by_key[(first, last)].id,
                    relationship=relationship,
                    is_primary=index == 0,
                    is_emergency=emergency,
                )
            )

    # Cross-household link: Margaret Reed is an emergency contact for Maya Patel.
    session.add(
        ChildGuardian(
            child_id=child_by_name[("Maya", "Patel")].id,
            guardian_id=guardian_by_key[("Margaret", "Reed")].id,
            relationship="Grandmother",
            is_primary=False,
            is_emergency=True,
        )
    )

    past_classes = [
        ClassGroup(
            ministry_year_id=past_year.id,
            name=name,
            age_band=age_band,
            age_min=age_min,
            age_max=age_max,
            lead_volunteer_id=volunteer_by_name["Rachel Kim"].id
            if name == "Toddlers"
            else (
                volunteer_by_name["James Taylor"].id
                if name == "Preschool"
                else volunteer_by_name["Naomi Johnson"].id
            ),
            room=room,
            curriculum=curriculum,
        )
        for name, age_band, age_min, age_max, room, curriculum in PAST_CLASSES
    ]
    current_classes = [
        ClassGroup(
            ministry_year_id=current_year.id,
            name=name,
            age_band=age_band,
            age_min=age_min,
            age_max=age_max,
            lead_volunteer_id=volunteer_by_name[CLASS_LEADS[name]].id,
            room=room,
            capacity=12,
            curriculum=curriculum,
        )
        for name, age_band, age_min, age_max, room, curriculum in CURRENT_CLASSES
    ]
    session.add_all([*past_classes, *current_classes])
    await session.flush()
    current_class_by_name = {item.name: item for item in current_classes}
    past_class_by_name = {item.name: item for item in past_classes}

    enrollments: list[Enrollment] = []
    current_enrollments: dict[str, list[Enrollment]] = {name: [] for name in current_class_by_name}
    for child_key, class_name in child_current_class.items():
        enrollment = Enrollment(
            child_id=child_by_name[child_key].id,
            class_id=current_class_by_name[class_name].id,
            start_date=date(2026, 9, 1),
        )
        enrollments.append(enrollment)
        current_enrollments[class_name].append(enrollment)
    for child_key, class_name in child_past_class.items():
        enrollments.append(
            Enrollment(
                child_id=child_by_name[child_key].id,
                class_id=past_class_by_name[class_name].id,
                start_date=date(2025, 9, 1),
                end_date=date(2026, 6, 30),
            )
        )
    session.add_all(enrollments)
    await session.flush()

    active_volunteers = [item for item in volunteers if item.status is VolunteerStatus.ACTIVE]
    sessions: list[ClassSession] = []
    session_class_names: dict[int, str] = {}
    for class_name, school_class in current_class_by_name.items():
        start_time = time(9, 0) if class_name in {"Nursery", "Preschool"} else time(11, 0)
        end_time = time(10, 15) if class_name in {"Nursery", "Preschool"} else time(12, 15)
        for index, session_date in enumerate(SESSIONS):
            topic = TOPICS[index % len(TOPICS)]
            class_session = ClassSession(
                class_id=school_class.id,
                date=session_date,
                start_time=start_time,
                end_time=end_time,
                topic=f"{topic} — {class_name}",
                notes="Demo lesson. Adjust as needed.",
                content_markdown=(
                    f"## {topic}\n\n"
                    f"Bible story and discussion for **{class_name}**.\n\n"
                    "### Take-home\n\n"
                    "Talk about the story as a family this week."
                ),
                resources=[
                    {
                        "label": "Colouring page",
                        "url": "https://example.com/colouring-page",
                    }
                ],
            )
            sessions.append(class_session)
            session_class_names[id(class_session)] = class_name
    session.add_all(sessions)
    await session.flush()

    session_volunteer_rows: list[SessionVolunteer] = []
    for index, class_session in enumerate(sessions):
        class_name = session_class_names[id(class_session)]
        lead = volunteer_by_name[CLASS_LEADS[class_name]]
        assistant = active_volunteers[(index + 1) % len(active_volunteers)]
        if assistant.id == lead.id:
            assistant = active_volunteers[(index + 2) % len(active_volunteers)]
        session_volunteer_rows.extend(
            [
                SessionVolunteer(class_session_id=class_session.id, volunteer_id=lead.id),
                SessionVolunteer(class_session_id=class_session.id, volunteer_id=assistant.id),
            ]
        )
    session.add_all(session_volunteer_rows)

    random = Random(42)  # noqa: S311 - deterministic demo data, not security
    attendance_rows: list[AttendanceRecord] = []
    visitor_count = 0
    for index, class_session in enumerate(sessions):
        class_name = session_class_names[id(class_session)]
        roster = current_enrollments[class_name]
        for child_index, enrollment in enumerate(roster):
            if (index + child_index) % 13 == 0:
                continue
            absent = (index + child_index) % 9 == 0
            attendance_rows.append(
                AttendanceRecord(
                    class_session_id=class_session.id,
                    child_id=enrollment.child_id,
                    status=AttendanceStatus.ABSENT if absent else AttendanceStatus.PRESENT,
                    note="Sick" if absent and random.random() < 0.5 else None,
                )
            )
        if class_session.date == SESSIONS[-1]:
            visitor_count += 1
            attendance_rows.append(
                AttendanceRecord(
                    class_session_id=class_session.id,
                    visitor_name=f"Visiting friend ({class_name})",
                    status=AttendanceStatus.PRESENT,
                )
            )
    session.add_all(attendance_rows)
    await session.commit()

    return SeedResult(
        ministry_years=2,
        volunteers=len(volunteers),
        households=len(households),
        guardians=len(guardians),
        children=len(children),
        classes=len(past_classes) + len(current_classes),
        enrollments=len(enrollments),
        sessions=len(sessions),
        session_volunteers=len(session_volunteer_rows),
        attendance=len(attendance_rows) - visitor_count,
        visitors=visitor_count,
    )

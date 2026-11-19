"""Attendance roster, visitors, reports, and not-seen contracts."""

from typing import Any

from httpx import AsyncClient

from tests.helpers import (
    create_child,
    create_class,
    create_guardian,
    create_session,
    create_year,
    enroll_child,
    link_guardian,
)


async def _setup(api_client: AsyncClient) -> dict[str, Any]:
    year = await create_year(api_client)
    school_class = await create_class(api_client, ministry_year_id=str(year["id"]))
    grace = await create_child(
        api_client,
        first_name="Grace",
        last_name="Hopper",
        allergies="Peanuts",
        medical_notes="Carries an inhaler",
        photo_consent="granted",
    )
    katherine = await create_child(
        api_client,
        first_name="Katherine",
        last_name="Johnson",
    )
    guardian = await create_guardian(api_client, first_name="Mary")
    await link_guardian(
        api_client,
        child_id=grace["id"],
        guardian_id=guardian["id"],
        relationship="Mother",
        is_primary=True,
        is_emergency=True,
    )
    for child in (grace, katherine):
        await enroll_child(api_client, class_id=str(school_class["id"]), child_id=str(child["id"]))
    session = await create_session(api_client, class_id=str(school_class["id"]))
    return {
        "year": year,
        "class": school_class,
        "grace": grace,
        "katherine": katherine,
        "session": session,
    }


async def test_roster_includes_safety_data_and_guardians(
    api_client: AsyncClient,
) -> None:
    setup = await _setup(api_client)

    response = await api_client.get(f"/v1/class-sessions/{setup['session']['id']}/attendance")

    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 2
    assert body["visitors"] == []
    assert body["summary"] == {
        "present": 0,
        "absent": 0,
        "not_recorded": 2,
        "recorded": 0,
        "visitors_present": 0,
        "visitors_absent": 0,
        "rate": None,
    }
    grace_entry = next(
        entry for entry in body["entries"] if entry["child"]["id"] == setup["grace"]["id"]
    )
    assert grace_entry["child"]["allergies"] == "Peanuts"
    assert grace_entry["child"]["medical_notes"] == "Carries an inhaler"
    assert grace_entry["guardians"][0]["relationship"] == "Mother"
    assert grace_entry["guardians"][0]["is_primary"] is True


async def test_bulk_upsert_and_summary(api_client: AsyncClient) -> None:
    setup = await _setup(api_client)
    url = f"/v1/class-sessions/{setup['session']['id']}/attendance"

    first = await api_client.put(
        url,
        json={
            "records": [
                {"child_id": setup["grace"]["id"], "status": "present"},
                {"child_id": setup["katherine"]["id"], "status": "absent"},
            ]
        },
    )
    assert first.status_code == 200
    summary = first.json()["summary"]
    assert summary["present"] == 1
    assert summary["absent"] == 1
    assert summary["recorded"] == 2
    assert summary["not_recorded"] == 0
    assert summary["rate"] == 0.5

    updated = await api_client.put(
        url,
        json={
            "records": [
                {
                    "child_id": setup["grace"]["id"],
                    "status": "absent",
                    "note": "Sick",
                }
            ]
        },
    )
    assert updated.status_code == 200
    assert updated.json()["summary"]["present"] == 0
    assert updated.json()["summary"]["rate"] == 0.0


async def test_visitors_are_replaced_on_each_submission(
    api_client: AsyncClient,
) -> None:
    setup = await _setup(api_client)
    url = f"/v1/class-sessions/{setup['session']['id']}/attendance"

    added = await api_client.put(
        url,
        json={
            "records": [],
            "visitors": [{"name": "Visiting Child"}],
        },
    )
    assert added.status_code == 200
    assert added.json()["summary"]["visitors_present"] == 1
    assert added.json()["visitors"][0]["visitor_name"] == "Visiting Child"

    removed = await api_client.put(
        url,
        json={"records": [], "visitors": []},
    )
    assert removed.status_code == 200
    assert removed.json()["visitors"] == []
    assert removed.json()["summary"]["visitors_present"] == 0


async def test_duplicate_and_unenrolled_children_are_rejected(
    api_client: AsyncClient,
) -> None:
    setup = await _setup(api_client)
    outsider = await create_child(api_client, first_name="Outside")
    url = f"/v1/class-sessions/{setup['session']['id']}/attendance"

    duplicate = await api_client.put(
        url,
        json={
            "records": [
                {"child_id": setup["grace"]["id"], "status": "present"},
                {"child_id": setup["grace"]["id"], "status": "absent"},
            ]
        },
    )
    assert duplicate.status_code == 422

    unenrolled = await api_client.put(
        url,
        json={"records": [{"child_id": outsider["id"], "status": "present"}]},
    )
    assert unenrolled.status_code == 422


async def test_calendar_changes_block_new_attendance_writes(
    api_client: AsyncClient,
) -> None:
    setup = await _setup(api_client)
    await api_client.patch(
        f"/v1/ministry-years/{setup['year']['id']}",
        json={"meeting_weekdays": [1]},
    )

    response = await api_client.put(
        f"/v1/class-sessions/{setup['session']['id']}/attendance",
        json={"records": [{"child_id": setup["grace"]["id"], "status": "present"}]},
    )

    assert response.status_code == 422
    assert "not a meeting day" in response.json()["detail"]


async def test_attendance_reports_for_class_and_child(api_client: AsyncClient) -> None:
    setup = await _setup(api_client)
    second_session = await create_session(
        api_client,
        class_id=str(setup["class"]["id"]),
        date="2026-09-13",
    )
    await api_client.put(
        f"/v1/class-sessions/{setup['session']['id']}/attendance",
        json={
            "records": [
                {"child_id": setup["grace"]["id"], "status": "present"},
                {"child_id": setup["katherine"]["id"], "status": "absent"},
            ],
            "visitors": [{"name": "Visitor"}],
        },
    )
    await api_client.put(
        f"/v1/class-sessions/{second_session['id']}/attendance",
        json={"records": [{"child_id": setup["grace"]["id"], "status": "present"}]},
    )

    report = await api_client.get(
        "/v1/reports/attendance",
        params={
            "from": "2026-09-01",
            "to": "2026-09-30",
            "class_id": setup["class"]["id"],
        },
    )
    assert report.status_code == 200
    body = report.json()
    assert body["present"] == 2
    assert body["absent"] == 1
    assert body["recorded"] == 3
    assert body["not_recorded"] == 1
    assert body["visitors_present"] == 1
    assert body["visitors_absent"] == 0
    assert body["rate"] == 0.6667

    child_report = await api_client.get(
        f"/v1/children/{setup['katherine']['id']}/attendance",
        params={"from": "2026-09-01", "to": "2026-09-30"},
    )
    assert child_report.status_code == 200
    assert child_report.json()["absent"] == 1
    assert child_report.json()["recorded"] == 1
    assert child_report.json()["not_recorded"] == 1
    assert child_report.json()["rate"] == 0.0


async def test_not_seen_report_tracks_children_without_present_attendance(
    api_client: AsyncClient,
) -> None:
    setup = await _setup(api_client)

    before = await api_client.get(
        "/v1/reports/not-seen",
        params={"since": "2026-09-01", "class_id": setup["class"]["id"]},
    )
    assert before.status_code == 200
    assert before.json()["total"] == 2

    await api_client.put(
        f"/v1/class-sessions/{setup['session']['id']}/attendance",
        json={
            "records": [
                {"child_id": setup["grace"]["id"], "status": "present"},
                {"child_id": setup["katherine"]["id"], "status": "absent"},
            ]
        },
    )
    after = await api_client.get(
        "/v1/reports/not-seen",
        params={"since": "2026-09-01", "class_id": setup["class"]["id"]},
    )
    assert after.json()["total"] == 1
    assert after.json()["items"][0]["child"]["id"] == setup["katherine"]["id"]

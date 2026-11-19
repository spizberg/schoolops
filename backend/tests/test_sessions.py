"""Class session, content, generation, and session volunteer contracts."""

from typing import Any

from httpx import AsyncClient

from tests.helpers import create_class, create_session, create_volunteer, create_year


async def _setup(client: AsyncClient) -> tuple[dict[str, Any], dict[str, Any]]:
    year = await create_year(client)
    school_class = await create_class(client, ministry_year_id=str(year["id"]))
    return year, school_class


async def test_create_session_with_lesson_content(api_client: AsyncClient) -> None:
    _, school_class = await _setup(api_client)

    session = await create_session(
        api_client,
        class_id=str(school_class["id"]),
        topic="Creation",
        content_markdown="# Creation\n\nGenesis 1.",
        resources=[{"label": "Colouring page", "url": "https://example.com/page"}],
    )

    assert session["topic"] == "Creation"
    assert session["content_markdown"].startswith("# Creation")
    assert session["resources"] == [{"label": "Colouring page", "url": "https://example.com/page"}]


async def test_session_rejects_non_meeting_days_and_closures(
    api_client: AsyncClient,
) -> None:
    year, school_class = await _setup(api_client)
    monday = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions",
        json={"date": "2026-09-07", "start_time": "09:00", "end_time": "10:30"},
    )
    assert monday.status_code == 422
    assert "not a meeting day" in monday.json()["detail"]

    await api_client.post(
        f"/v1/ministry-years/{year['id']}/no-class-days",
        json={"date": "2026-09-06", "name": "Church picnic"},
    )
    closure = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions",
        json={"date": "2026-09-06", "start_time": "09:00", "end_time": "10:30"},
    )
    assert closure.status_code == 422


async def test_session_must_fall_inside_the_year(api_client: AsyncClient) -> None:
    _, school_class = await _setup(api_client)

    response = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions",
        json={"date": "2027-07-04", "start_time": "09:00", "end_time": "10:30"},
    )

    assert response.status_code == 422
    assert "inside the class's ministry year" in response.json()["detail"]


async def test_start_time_must_be_before_end_time(api_client: AsyncClient) -> None:
    _, school_class = await _setup(api_client)

    response = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions",
        json={"date": "2026-09-06", "start_time": "11:00", "end_time": "10:00"},
    )

    assert response.status_code == 422
    assert "before the end time" in response.json()["detail"]


async def test_sessions_are_unique_per_class_date_and_start(
    api_client: AsyncClient,
) -> None:
    _, school_class = await _setup(api_client)
    await create_session(api_client, class_id=str(school_class["id"]))

    duplicate = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions",
        json={"date": "2026-09-06", "start_time": "09:00", "end_time": "10:30"},
    )
    assert duplicate.status_code == 409

    later = await create_session(
        api_client,
        class_id=str(school_class["id"]),
        start_time="11:00:00",
        end_time="12:00:00",
    )
    assert later["start_time"] == "11:00:00"


async def test_list_update_and_delete_sessions(api_client: AsyncClient) -> None:
    _, school_class = await _setup(api_client)
    session = await create_session(api_client, class_id=str(school_class["id"]))

    listed = await api_client.get(
        f"/v1/classes/{school_class['id']}/sessions",
        params={"from": "2026-09-01", "to": "2026-09-30"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = await api_client.patch(
        f"/v1/class-sessions/{session['id']}",
        json={"topic": "Updated topic", "content_markdown": "New lesson"},
    )
    assert updated.status_code == 200
    assert updated.json()["topic"] == "Updated topic"

    moved_to_monday = await api_client.patch(
        f"/v1/class-sessions/{session['id']}", json={"date": "2026-09-07"}
    )
    assert moved_to_monday.status_code == 422

    deleted = await api_client.delete(f"/v1/class-sessions/{session['id']}")
    assert deleted.status_code == 204
    missing = await api_client.get(f"/v1/class-sessions/{session['id']}")
    assert missing.status_code == 404


async def test_bulk_generation_skips_closures_and_existing_sessions(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client, start_date="2026-09-01", end_date="2026-09-30")
    school_class = await create_class(api_client, ministry_year_id=str(year["id"]))
    await api_client.post(
        f"/v1/ministry-years/{year['id']}/no-class-days",
        json={"date": "2026-09-13", "name": "Church picnic"},
    )
    payload = {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "start_time": "09:00",
        "end_time": "10:30",
        "weekdays": [],
    }

    first = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions/generate", json=payload
    )
    assert first.status_code == 200
    assert first.json()["created"] == 3

    second = await api_client.post(
        f"/v1/classes/{school_class['id']}/sessions/generate", json=payload
    )
    assert second.json()["created"] == 0
    assert second.json()["skipped"] == 3

    listed = await api_client.get(
        f"/v1/classes/{school_class['id']}/sessions",
        params={"from": "2026-09-01", "to": "2026-09-30"},
    )
    assert [item["date"] for item in listed.json()["items"]] == [
        "2026-09-06",
        "2026-09-20",
        "2026-09-27",
    ]


async def test_session_volunteers_can_be_recorded_and_replaced(
    api_client: AsyncClient,
) -> None:
    _, school_class = await _setup(api_client)
    session = await create_session(api_client, class_id=str(school_class["id"]))
    first = await create_volunteer(api_client)
    second = await create_volunteer(
        api_client,
        email="second@cbsg.org",
        first_name="Alan",
        last_name="Turing",
        phone="+33 6 22 22 22 22",
    )

    saved = await api_client.put(
        f"/v1/class-sessions/{session['id']}/volunteers",
        json={"volunteer_ids": [first["id"], second["id"]]},
    )
    assert saved.status_code == 200
    assert [item["volunteer"]["id"] for item in saved.json()["volunteers"]] == [
        first["id"],
        second["id"],
    ]

    replaced = await api_client.put(
        f"/v1/class-sessions/{session['id']}/volunteers",
        json={"volunteer_ids": [second["id"]]},
    )
    assert [item["volunteer_id"] for item in replaced.json()["volunteers"]] == [second["id"]]

    duplicate = await api_client.put(
        f"/v1/class-sessions/{session['id']}/volunteers",
        json={"volunteer_ids": [first["id"], first["id"]]},
    )
    assert duplicate.status_code == 422

    await api_client.delete(f"/v1/volunteers/{first['id']}")
    inactive = await api_client.put(
        f"/v1/class-sessions/{session['id']}/volunteers",
        json={"volunteer_ids": [first["id"]]},
    )
    assert inactive.status_code == 422
    assert "active volunteers" in inactive.json()["detail"]

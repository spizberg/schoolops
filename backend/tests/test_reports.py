"""Dashboard and CSV export contracts."""

import csv
import io
from datetime import date, timedelta
from typing import Any

from httpx import AsyncClient

from tests.helpers import (
    create_child,
    create_class,
    create_session,
    create_volunteer,
    create_year,
    enroll_child,
)


async def test_dashboard_reports_counts_today_and_recently_missing(
    api_client: AsyncClient,
) -> None:
    today = date.today()
    year = await create_year(
        api_client,
        label="Current",
        start_date=(today - timedelta(days=30)).isoformat(),
        end_date=(today + timedelta(days=30)).isoformat(),
        meeting_weekdays=[today.isoweekday()],
        is_active=True,
    )
    volunteer = await create_volunteer(api_client)
    school_class = await create_class(
        api_client,
        ministry_year_id=str(year["id"]),
        lead_volunteer_id=str(volunteer["id"]),
    )
    present_child = await create_child(api_client, first_name="Grace")
    absent_child = await create_child(api_client, first_name="Katherine", last_name="Johnson")
    await enroll_child(
        api_client,
        class_id=str(school_class["id"]),
        child_id=str(present_child["id"]),
        start_date=(today - timedelta(days=1)).isoformat(),
    )
    await enroll_child(
        api_client,
        class_id=str(school_class["id"]),
        child_id=str(absent_child["id"]),
        start_date=(today - timedelta(days=1)).isoformat(),
    )
    session = await create_session(
        api_client,
        class_id=str(school_class["id"]),
        date=today.isoformat(),
        start_time="09:00:00",
        end_time="10:00:00",
        topic="Today's lesson",
    )
    await api_client.put(
        f"/v1/class-sessions/{session['id']}/volunteers",
        json={"volunteer_ids": [volunteer["id"]]},
    )
    await api_client.put(
        f"/v1/class-sessions/{session['id']}/attendance",
        json={
            "records": [
                {"child_id": present_child["id"], "status": "present"},
                {"child_id": absent_child["id"], "status": "absent"},
            ]
        },
    )

    response = await api_client.get("/v1/reports/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["active_year"]["id"] == year["id"]
    assert body["counts"] == {"children": 2, "volunteers": 1, "classes": 1}
    assert body["todays_sessions"][0]["class_name"] == school_class["name"]
    assert body["todays_sessions"][0]["volunteers"] == 1
    assert body["attendance_recorded_today"] == 2
    assert body["not_seen_recently"] == 1


async def _setup_csv(api_client: AsyncClient) -> dict[str, Any]:
    year = await create_year(api_client)
    school_class = await create_class(api_client, ministry_year_id=str(year["id"]))
    grace = await create_child(api_client, first_name="Grace", last_name="Hopper, Jr.")
    katherine = await create_child(api_client, first_name="Katherine", last_name="Johnson")
    for child in (grace, katherine):
        await enroll_child(api_client, class_id=str(school_class["id"]), child_id=str(child["id"]))
    first = await create_session(api_client, class_id=str(school_class["id"]))
    second = await create_session(
        api_client,
        class_id=str(school_class["id"]),
        date="2026-09-13",
    )
    await api_client.put(
        f"/v1/class-sessions/{first['id']}/attendance",
        json={
            "records": [
                {"child_id": grace["id"], "status": "present"},
                {"child_id": katherine["id"], "status": "absent"},
            ]
        },
    )
    await api_client.put(
        f"/v1/class-sessions/{second['id']}/attendance",
        json={"records": [{"child_id": grace["id"], "status": "present"}]},
    )
    return {
        "class": school_class,
        "grace": grace,
        "katherine": katherine,
    }


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


async def test_attendance_csv_has_per_child_totals(api_client: AsyncClient) -> None:
    setup = await _setup_csv(api_client)

    response = await api_client.get(
        "/v1/reports/attendance.csv",
        params={
            "from": "2026-09-01",
            "to": "2026-09-30",
            "class_id": setup["class"]["id"],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        'filename="attendance_2026-09-01_2026-09-30.csv"' in response.headers["content-disposition"]
    )
    rows = _rows(response.text)
    assert rows[0] == [
        "child",
        "last_present_on",
        "present",
        "absent",
        "not_recorded",
        "recorded",
        "rate",
    ]
    assert rows[1] == [
        "Grace Hopper, Jr.",
        "2026-09-13",
        "2",
        "0",
        "0",
        "2",
        "1.0000",
    ]
    assert rows[2] == [
        "Katherine Johnson",
        "",
        "0",
        "1",
        "1",
        "1",
        "0.0000",
    ]


async def test_attendance_csv_for_one_child(api_client: AsyncClient) -> None:
    setup = await _setup_csv(api_client)

    response = await api_client.get(
        "/v1/reports/attendance.csv",
        params={
            "from": "2026-09-01",
            "to": "2026-09-30",
            "child_id": setup["katherine"]["id"],
        },
    )

    assert response.status_code == 200
    rows = _rows(response.text)
    assert len(rows) == 2
    assert rows[1][0] == "Katherine Johnson"
    assert rows[1][5] == "1"

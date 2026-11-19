"""Ministry year and calendar API contracts."""

from httpx import AsyncClient

from tests.helpers import create_year


async def test_create_year_defaults_to_sunday_and_is_inactive(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/v1/ministry-years",
        json={"label": "2026-2027", "start_date": "2026-09-01", "end_date": "2027-06-30"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["meeting_weekdays"] == [7]
    assert body["is_active"] is False
    assert response.headers["location"] == f"/v1/ministry-years/{body['id']}"


async def test_start_date_must_be_before_end_date(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/v1/ministry-years",
        json={"label": "2026", "start_date": "2026-09-01", "end_date": "2026-09-01"},
    )

    assert response.status_code == 422
    assert "strictly before" in response.json()["detail"]


async def test_label_is_unique(api_client: AsyncClient) -> None:
    await create_year(api_client)

    response = await api_client.post(
        "/v1/ministry-years",
        json={"label": "2026-2027", "start_date": "2027-09-01", "end_date": "2028-06-30"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


async def test_activating_a_year_deactivates_the_previous_one(
    api_client: AsyncClient,
) -> None:
    first = await create_year(api_client, label="2025-2026", is_active=True)
    second = await create_year(
        api_client,
        label="2026-2027",
        start_date="2026-09-01",
        end_date="2027-06-30",
    )

    response = await api_client.post(f"/v1/ministry-years/{second['id']}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    refreshed = await api_client.get(f"/v1/ministry-years/{first['id']}")
    assert refreshed.json()["is_active"] is False


async def test_no_class_day_must_fall_inside_the_year(api_client: AsyncClient) -> None:
    year = await create_year(api_client)

    response = await api_client.post(
        f"/v1/ministry-years/{year['id']}/no-class-days",
        json={"date": "2027-07-04", "name": "Outside"},
    )

    assert response.status_code == 422
    assert "inside its ministry year" in response.json()["detail"]


async def test_no_class_day_crud(api_client: AsyncClient) -> None:
    year = await create_year(api_client)

    created = await api_client.post(
        f"/v1/ministry-years/{year['id']}/no-class-days",
        json={"date": "2026-09-13", "name": "Church picnic", "kind": "other"},
    )
    assert created.status_code == 201
    day = created.json()
    assert day["kind"] == "other"

    duplicate = await api_client.post(
        f"/v1/ministry-years/{year['id']}/no-class-days",
        json={"date": "2026-09-13", "name": "Duplicate"},
    )
    assert duplicate.status_code == 409

    listed = await api_client.get(f"/v1/ministry-years/{year['id']}/no-class-days")
    assert [item["id"] for item in listed.json()] == [day["id"]]

    deleted = await api_client.delete(f"/v1/no-class-days/{day['id']}")
    assert deleted.status_code == 204

    listed = await api_client.get(f"/v1/ministry-years/{year['id']}/no-class-days")
    assert listed.json() == []


async def test_meeting_days_exclude_closures_and_non_sundays(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client, start_date="2026-09-01", end_date="2026-09-30")
    await api_client.post(
        f"/v1/ministry-years/{year['id']}/no-class-days",
        json={"date": "2026-09-13", "name": "Church picnic"},
    )

    response = await api_client.get(
        f"/v1/ministry-years/{year['id']}/meeting-days",
        params={"from": "2026-09-01", "to": "2026-09-30"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == ["2026-09-06", "2026-09-20", "2026-09-27"]


async def test_meeting_days_are_clamped_to_the_year(api_client: AsyncClient) -> None:
    year = await create_year(api_client, start_date="2026-09-01", end_date="2026-09-30")

    response = await api_client.get(
        f"/v1/ministry-years/{year['id']}/meeting-days",
        params={"from": "2026-08-01", "to": "2026-10-31"},
    )

    assert response.json()["items"] == [
        "2026-09-06",
        "2026-09-13",
        "2026-09-20",
        "2026-09-27",
    ]

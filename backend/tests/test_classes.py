"""Class, age-band, and enrollment API contracts."""

from httpx import AsyncClient

from tests.helpers import (
    create_child,
    create_class,
    create_volunteer,
    create_year,
    enroll_child,
)


async def test_class_name_is_unique_within_a_year_but_not_across_years(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client)
    other_year = await create_year(
        api_client,
        label="2027-2028",
        start_date="2027-09-01",
        end_date="2028-06-30",
    )
    await create_class(api_client, ministry_year_id=year["id"], name="Preschool")

    duplicate = await api_client.post(
        "/v1/classes",
        json={
            "ministry_year_id": year["id"],
            "name": "Preschool",
            "age_band": "3-5 years",
        },
    )
    assert duplicate.status_code == 409

    allowed = await api_client.post(
        "/v1/classes",
        json={
            "ministry_year_id": other_year["id"],
            "name": "Preschool",
            "age_band": "3-5 years",
        },
    )
    assert allowed.status_code == 201


async def test_age_range_is_validated(api_client: AsyncClient) -> None:
    year = await create_year(api_client)

    response = await api_client.post(
        "/v1/classes",
        json={
            "ministry_year_id": year["id"],
            "name": "Preschool",
            "age_band": "3-5 years",
            "age_min": 6,
            "age_max": 5,
        },
    )

    assert response.status_code == 422
    assert "Minimum age" in response.json()["detail"]


async def test_inactive_volunteer_cannot_lead_a_new_class(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client)
    volunteer = await create_volunteer(api_client)
    await api_client.delete(f"/v1/volunteers/{volunteer['id']}")

    response = await api_client.post(
        "/v1/classes",
        json={
            "ministry_year_id": year["id"],
            "name": "Preschool",
            "age_band": "3-5 years",
            "lead_volunteer_id": volunteer["id"],
        },
    )

    assert response.status_code == 422
    assert "inactive volunteer" in response.json()["detail"]


async def test_capacity_is_informational_and_roster_reflects_dates(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client)
    school_class = await create_class(api_client, ministry_year_id=year["id"], capacity=1)
    first = await create_child(api_client, first_name="Grace")
    second = await create_child(api_client, first_name="Katherine", last_name="Johnson")

    first_enrollment = await enroll_child(
        api_client,
        class_id=school_class["id"],
        child_id=first["id"],
        start_date="2026-09-01",
    )
    await enroll_child(
        api_client,
        class_id=school_class["id"],
        child_id=second["id"],
        start_date="2026-09-01",
    )

    roster = await api_client.get(
        f"/v1/classes/{school_class['id']}/enrollments",
        params={"on_date": "2026-09-06"},
    )
    assert roster.status_code == 200
    assert roster.json()["total"] == 2

    await api_client.patch(
        f"/v1/enrollments/{first_enrollment['id']}",
        json={"end_date": "2026-09-10"},
    )
    after_end = await api_client.get(
        f"/v1/classes/{school_class['id']}/enrollments",
        params={"on_date": "2026-09-13"},
    )
    assert after_end.json()["total"] == 1


async def test_child_has_one_active_class_per_ministry_year(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client)
    first_class = await create_class(api_client, ministry_year_id=year["id"], name="Preschool")
    second_class = await create_class(api_client, ministry_year_id=year["id"], name="Kindergarten")
    child = await create_child(api_client)
    await enroll_child(api_client, class_id=first_class["id"], child_id=child["id"])

    response = await api_client.post(
        f"/v1/classes/{second_class['id']}/enrollments",
        json={"child_id": child["id"], "start_date": "2026-09-01"},
    )

    assert response.status_code == 409
    assert "active class in this ministry year" in response.json()["detail"]


async def test_class_with_history_cannot_be_deleted(api_client: AsyncClient) -> None:
    year = await create_year(api_client)
    school_class = await create_class(api_client, ministry_year_id=year["id"])
    child = await create_child(api_client)
    await enroll_child(api_client, class_id=school_class["id"], child_id=child["id"])

    blocked = await api_client.delete(f"/v1/classes/{school_class['id']}")
    assert blocked.status_code == 409

    empty = await create_class(api_client, ministry_year_id=year["id"], name="Empty Class")
    deleted = await api_client.delete(f"/v1/classes/{empty['id']}")
    assert deleted.status_code == 204

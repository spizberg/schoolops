"""Child API contracts."""

from httpx import AsyncClient

from tests.helpers import (
    create_child,
    create_class,
    create_guardian,
    create_household,
    create_year,
    enroll_child,
    link_guardian,
)


async def test_create_child_with_safety_fields(api_client: AsyncClient) -> None:
    household = await create_household(api_client)

    child = await create_child(
        api_client,
        household_id=household["id"],
        date_of_birth="2018-03-14",
        grade="Year 2",
        allergies="Peanuts",
        medical_notes="Carries an inhaler",
        photo_consent="denied",
    )

    assert child["household_id"] == household["id"]
    assert child["date_of_birth"] == "2018-03-14"
    assert child["allergies"] == "Peanuts"
    assert child["medical_notes"] == "Carries an inhaler"
    assert child["photo_consent"] == "denied"
    assert "admission_no" not in child


async def test_date_of_birth_is_required(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/v1/children",
        json={"first_name": "Grace", "last_name": "Hopper"},
    )

    assert response.status_code == 422


async def test_child_search_filters_household_class_and_status(
    api_client: AsyncClient,
) -> None:
    year = await create_year(api_client)
    school_class = await create_class(api_client, ministry_year_id=year["id"])
    first_household = await create_household(api_client, name="House A")
    second_household = await create_household(api_client, name="House B")
    first = await create_child(
        api_client,
        first_name="Grace",
        household_id=first_household["id"],
    )
    second = await create_child(
        api_client,
        first_name="Katherine",
        last_name="Johnson",
        household_id=second_household["id"],
    )
    await enroll_child(api_client, class_id=school_class["id"], child_id=first["id"])
    await api_client.patch(f"/v1/children/{second['id']}", json={"status": "inactive"})

    by_name = await api_client.get("/v1/children", params={"q": "johnson"})
    assert by_name.json()["total"] == 1

    by_household = await api_client.get(
        "/v1/children", params={"household_id": first_household["id"]}
    )
    assert by_household.json()["total"] == 1
    assert by_household.json()["items"][0]["id"] == first["id"]

    by_class = await api_client.get("/v1/children", params={"class_id": school_class["id"]})
    assert by_class.json()["total"] == 1

    active = await api_client.get("/v1/children", params={"status": "active"})
    assert active.json()["total"] == 1


async def test_guardian_count_reflects_links(api_client: AsyncClient) -> None:
    child = await create_child(api_client)
    guardian = await create_guardian(api_client)
    await link_guardian(api_client, child_id=child["id"], guardian_id=guardian["id"])

    detail = await api_client.get(f"/v1/children/{child['id']}")
    assert detail.json()["guardian_count"] == 1

    listed = await api_client.get("/v1/children")
    assert listed.json()["items"][0]["guardian_count"] == 1


async def test_activation_without_guardian_warns_but_succeeds(
    api_client: AsyncClient,
) -> None:
    child = await create_child(api_client)
    await api_client.patch(f"/v1/children/{child['id']}", json={"status": "inactive"})
    reactivated = await api_client.patch(f"/v1/children/{child['id']}", json={"status": "active"})

    assert reactivated.status_code == 200
    assert reactivated.headers["x-cbsg-warning"] == ("This active child has no guardian contact.")

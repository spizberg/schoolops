"""Household and guardian API contracts."""

from httpx import AsyncClient

from tests.helpers import (
    create_child,
    create_guardian,
    create_household,
    link_guardian,
)


async def test_household_crud_and_search(api_client: AsyncClient) -> None:
    household = await create_household(
        api_client, name="The Hopper family", address="12 Church Lane"
    )

    listed = await api_client.get("/v1/households", params={"q": "hopper"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == household["id"]

    updated = await api_client.patch(
        f"/v1/households/{household['id']}", json={"notes": "Gate code 1234"}
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Gate code 1234"


async def test_guardian_crud_and_search(api_client: AsyncClient) -> None:
    household = await create_household(api_client)
    guardian = await create_guardian(
        api_client,
        household_id=household["id"],
        email="MARY@Example.com",
    )
    assert guardian["email"] == "mary@example.com"

    searched = await api_client.get("/v1/guardians", params={"q": "12 34"})
    assert searched.status_code == 200
    assert searched.json()["total"] == 1

    updated = await api_client.patch(
        f"/v1/guardians/{guardian['id']}",
        json={"phone": "+33 7 00 00 00 00", "notes": "Preferred contact"},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+33 7 00 00 00 00"

    deleted = await api_client.delete(f"/v1/guardians/{guardian['id']}")
    assert deleted.status_code == 204
    listed = await api_client.get("/v1/guardians")
    assert listed.json()["total"] == 0


async def test_guardians_can_link_across_households(api_client: AsyncClient) -> None:
    first_household = await create_household(api_client, name="House A")
    second_household = await create_household(api_client, name="House B")
    child = await create_child(api_client, household_id=first_household["id"])
    guardian = await create_guardian(
        api_client, household_id=second_household["id"], first_name="Alice"
    )

    link = await link_guardian(
        api_client,
        child_id=child["id"],
        guardian_id=guardian["id"],
        relationship="Grandmother",
        is_primary=True,
        is_emergency=True,
    )

    assert link["guardian"]["id"] == guardian["id"]
    assert link["guardian"]["household_id"] == second_household["id"]
    assert link["is_primary"] is True
    detail = await api_client.get(f"/v1/children/{child['id']}")
    assert detail.json()["guardian_count"] == 1


async def test_one_primary_guardian_per_child(api_client: AsyncClient) -> None:
    child = await create_child(api_client)
    first = await create_guardian(api_client, first_name="Mary")
    second = await create_guardian(api_client, first_name="John", last_name="Hopper")
    first_link = await link_guardian(
        api_client,
        child_id=child["id"],
        guardian_id=first["id"],
        is_primary=True,
    )
    second_link = await link_guardian(
        api_client,
        child_id=child["id"],
        guardian_id=second["id"],
        relationship="Father",
        is_primary=True,
    )
    assert second_link["is_primary"] is True

    links = await api_client.get(f"/v1/children/{child['id']}/guardians")
    assert links.status_code == 200
    assert [item["is_primary"] for item in links.json()] == [True, False]

    promoted = await api_client.post(f"/v1/child-guardians/{first_link['id']}/set-primary")
    assert promoted.status_code == 200
    assert promoted.json()["is_primary"] is True

    links = await api_client.get(f"/v1/children/{child['id']}/guardians")
    assert [item["is_primary"] for item in links.json()] == [True, False]


async def test_duplicate_guardian_link_is_rejected(api_client: AsyncClient) -> None:
    child = await create_child(api_client)
    guardian = await create_guardian(api_client)
    await link_guardian(api_client, child_id=child["id"], guardian_id=guardian["id"])

    response = await api_client.post(
        f"/v1/children/{child['id']}/guardians",
        json={
            "guardian_id": guardian["id"],
            "relationship": "Mother",
        },
    )

    assert response.status_code == 409


async def test_child_activation_warns_without_guardian(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/v1/children",
        json={
            "first_name": "Grace",
            "last_name": "Hopper",
            "date_of_birth": "2018-03-14",
        },
    )

    assert response.status_code == 201
    assert response.headers["x-cbsg-warning"] == ("This active child has no guardian contact.")

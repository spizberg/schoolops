"""Volunteer API contracts."""

from httpx import AsyncClient

from tests.helpers import create_volunteer


async def test_create_volunteer_normalizes_and_requires_phone(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/v1/volunteers",
        json={
            "first_name": " Ada ",
            "last_name": "Lovelace",
            "phone": "+33 6 11 11 11 11",
            "email": "Ada@Example.COM",
            "joined_on": "2025-01-15",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["first_name"] == "Ada"
    assert body["email"] == "ada@example.com"
    assert body["status"] == "active"
    assert response.headers["location"] == f"/v1/volunteers/{body['id']}"

    missing_phone = await api_client.post(
        "/v1/volunteers",
        json={"first_name": "No", "last_name": "Phone"},
    )
    assert missing_phone.status_code == 422


async def test_email_is_optional_but_unique_when_present(
    api_client: AsyncClient,
) -> None:
    first = await create_volunteer(api_client, email=None)
    second = await create_volunteer(
        api_client,
        email=None,
        first_name="Alan",
        last_name="Turing",
        phone="+33 6 22 22 22 22",
    )
    assert first["email"] is None
    assert second["email"] is None

    await create_volunteer(api_client, email="ada@example.com")
    duplicate = await api_client.post(
        "/v1/volunteers",
        json={
            "first_name": "Ada",
            "last_name": "Byron",
            "phone": "+33 6 33 33 33 33",
            "email": "ADA@example.com",
        },
    )
    assert duplicate.status_code == 409


async def test_search_and_status_filter(api_client: AsyncClient) -> None:
    await create_volunteer(api_client, email="ada@example.com", first_name="Ada")
    await create_volunteer(
        api_client,
        email="alan@example.com",
        first_name="Alan",
        last_name="Turing",
        phone="+33 6 22 22 22 22",
    )

    searched = await api_client.get("/v1/volunteers", params={"q": "turing"})
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["first_name"] == "Alan"

    deactivated = searched.json()["items"][0]["id"]
    await api_client.patch(f"/v1/volunteers/{deactivated}", json={"status": "inactive"})

    active = await api_client.get("/v1/volunteers", params={"status": "active"})
    assert active.json()["total"] == 1
    assert active.json()["items"][0]["first_name"] == "Ada"


async def test_delete_deactivates_instead_of_removing(api_client: AsyncClient) -> None:
    volunteer = await create_volunteer(api_client)

    response = await api_client.delete(f"/v1/volunteers/{volunteer['id']}")

    assert response.status_code == 204
    refreshed = await api_client.get(f"/v1/volunteers/{volunteer['id']}")
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "inactive"


async def test_email_can_be_cleared(api_client: AsyncClient) -> None:
    volunteer = await create_volunteer(api_client, email="volunteer@example.com")

    response = await api_client.patch(f"/v1/volunteers/{volunteer['id']}", json={"email": None})

    assert response.status_code == 200
    assert response.json()["email"] is None

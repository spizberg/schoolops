"""Small API helpers shared by integration tests."""

from typing import Any, cast

from httpx import AsyncClient


async def create_year(
    client: AsyncClient,
    *,
    label: str = "2026-2027",
    start_date: str = "2026-09-01",
    end_date: str = "2027-06-30",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/ministry-years",
        json={
            "label": label,
            "start_date": start_date,
            "end_date": end_date,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def create_volunteer(
    client: AsyncClient,
    *,
    phone: str = "+33 6 11 11 11 11",
    email: str | None = "volunteer@cbsg.org",
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/volunteers",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "email": email,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def create_household(
    client: AsyncClient,
    *,
    name: str | None = "The Hopper family",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/households",
        json={"name": name, **extra},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def create_guardian(
    client: AsyncClient,
    *,
    first_name: str = "Mary",
    last_name: str = "Hopper",
    phone: str = "+33 6 12 34 56 78",
    email: str | None = None,
    household_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/guardians",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "email": email,
            "household_id": household_id,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def create_child(
    client: AsyncClient,
    *,
    first_name: str = "Grace",
    last_name: str = "Hopper",
    date_of_birth: str = "2018-03-14",
    household_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/children",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
            "household_id": household_id,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def link_guardian(
    client: AsyncClient,
    *,
    child_id: str,
    guardian_id: str,
    relationship: str = "Mother",
    is_primary: bool = False,
    is_emergency: bool = False,
) -> dict[str, Any]:
    response = await client.post(
        f"/v1/children/{child_id}/guardians",
        json={
            "guardian_id": guardian_id,
            "relationship": relationship,
            "is_primary": is_primary,
            "is_emergency": is_emergency,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def create_class(
    client: AsyncClient,
    *,
    ministry_year_id: str,
    name: str = "Preschool",
    age_band: str = "3-5 years",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/classes",
        json={
            "ministry_year_id": ministry_year_id,
            "name": name,
            "age_band": age_band,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def enroll_child(
    client: AsyncClient,
    *,
    class_id: str,
    child_id: str,
    start_date: str = "2026-09-01",
    end_date: str | None = None,
) -> dict[str, Any]:
    response = await client.post(
        f"/v1/classes/{class_id}/enrollments",
        json={
            "child_id": child_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def create_session(
    client: AsyncClient,
    *,
    class_id: str,
    date: str = "2026-09-06",
    start_time: str = "09:00:00",
    end_time: str = "10:30:00",
    **extra: Any,
) -> dict[str, Any]:
    response = await client.post(
        f"/v1/classes/{class_id}/sessions",
        json={
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())

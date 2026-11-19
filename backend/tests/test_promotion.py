"""Annual promotion preview and apply contracts."""

from typing import Any

from httpx import AsyncClient

from tests.helpers import create_child, create_class, create_year, enroll_child


async def _setup(api_client: AsyncClient) -> dict[str, Any]:
    source = await create_year(
        api_client,
        label="2025-2026",
        start_date="2025-09-01",
        end_date="2026-06-30",
    )
    target = await create_year(
        api_client,
        label="2026-2027",
        start_date="2026-09-01",
        end_date="2027-06-30",
    )
    source_preschool = await create_class(
        api_client,
        ministry_year_id=source["id"],
        name="Preschool",
        age_band="3-5 years",
        age_min=3,
        age_max=5,
    )
    source_unmapped = await create_class(
        api_client,
        ministry_year_id=source["id"],
        name="Toddlers",
        age_band="1-2 years",
        age_min=1,
        age_max=2,
    )
    target_kindergarten = await create_class(
        api_client,
        ministry_year_id=target["id"],
        name="Kindergarten",
        age_band="5-6 years",
        age_min=5,
        age_max=6,
    )
    target_primary = await create_class(
        api_client,
        ministry_year_id=target["id"],
        name="Primary",
        age_band="7-9 years",
        age_min=7,
        age_max=9,
    )

    moving = await create_child(
        api_client,
        first_name="Grace",
        last_name="Hopper",
        date_of_birth="2020-01-01",
    )
    already = await create_child(
        api_client,
        first_name="Katherine",
        last_name="Johnson",
        date_of_birth="2020-04-01",
    )
    unmatched = await create_child(
        api_client,
        first_name="Tiny",
        last_name="Toddler",
        date_of_birth="2024-01-01",
    )
    await enroll_child(
        api_client,
        class_id=source_preschool["id"],
        child_id=moving["id"],
        start_date="2025-09-01",
    )
    await enroll_child(
        api_client,
        class_id=source_preschool["id"],
        child_id=already["id"],
        start_date="2025-09-01",
    )
    await enroll_child(
        api_client,
        class_id=target_kindergarten["id"],
        child_id=already["id"],
        start_date="2026-09-01",
    )
    await enroll_child(
        api_client,
        class_id=source_unmapped["id"],
        child_id=unmatched["id"],
        start_date="2025-09-01",
    )

    return {
        "source": source,
        "target": target,
        "source_preschool": source_preschool,
        "source_unmapped": source_unmapped,
        "target_kindergarten": target_kindergarten,
        "target_primary": target_primary,
        "moving": moving,
        "already": already,
        "unmatched": unmatched,
        "payload": {
            "source_year_id": source["id"],
            "target_year_id": target["id"],
            "mappings": [
                {
                    "source_class_id": source_preschool["id"],
                    "target_class_id": target_kindergarten["id"],
                }
            ],
        },
    }


async def test_promotion_preview_reports_assignments_and_exceptions(
    api_client: AsyncClient,
) -> None:
    setup = await _setup(api_client)

    response = await api_client.post("/v1/promotions/preview", json=setup["payload"])

    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {"assign": 1, "unmatched": 1, "already_enrolled": 1}
    assignment = body["assignments"][0]
    assert assignment["child_id"] == setup["moving"]["id"]
    assert assignment["target_class_name"] == "Kindergarten"
    assert assignment["age_at_target_start"] == 6
    assert body["already_enrolled"][0]["child_id"] == setup["already"]["id"]
    assert body["unmatched"][0]["child_id"] == setup["unmatched"]["id"]
    assert "not mapped" in body["unmatched"][0]["reason"]


async def test_promotion_apply_is_idempotent(api_client: AsyncClient) -> None:
    setup = await _setup(api_client)

    first = await api_client.post("/v1/promotions/apply", json=setup["payload"])
    assert first.status_code == 200
    assert first.json()["created"] == 1
    assert first.json()["skipped"] == 1

    second = await api_client.post("/v1/promotions/apply", json=setup["payload"])
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["skipped"] == 2

    children = await api_client.get(
        "/v1/children",
        params={"class_id": setup["target_kindergarten"]["id"]},
    )
    assert children.json()["total"] == 2


async def test_promotion_rejects_invalid_year_mappings(api_client: AsyncClient) -> None:
    setup = await _setup(api_client)

    same_year = await api_client.post(
        "/v1/promotions/preview",
        json={
            "source_year_id": setup["source"]["id"],
            "target_year_id": setup["source"]["id"],
            "mappings": [
                {
                    "source_class_id": setup["source_preschool"]["id"],
                    "target_class_id": setup["target_kindergarten"]["id"],
                }
            ],
        },
    )
    assert same_year.status_code == 422

    wrong_target = await api_client.post(
        "/v1/promotions/preview",
        json={
            "source_year_id": setup["source"]["id"],
            "target_year_id": setup["target"]["id"],
            "mappings": [
                {
                    "source_class_id": setup["source_preschool"]["id"],
                    "target_class_id": setup["source_unmapped"]["id"],
                }
            ],
        },
    )
    assert wrong_target.status_code == 422

"""Demo data seeding contracts."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.db.models import AttendanceRecord, Child, ClassGroup, ClassSession
from schoolops.seed import DemoDataExistsError, seed_demo


async def test_seed_demo_creates_usable_data(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    result = await seed_demo(db_session)

    assert result.ministry_years == 2
    assert result.volunteers == 12
    assert result.households == 15
    assert result.children == 24
    assert result.classes == 7
    assert result.sessions == 44
    assert result.attendance > 100
    assert result.visitors == 4

    assert await db_session.scalar(select(func.count()).select_from(Child)) == 24
    assert await db_session.scalar(select(func.count()).select_from(ClassGroup)) == 7
    assert await db_session.scalar(select(func.count()).select_from(ClassSession)) == 44
    attendance_count = await db_session.scalar(select(func.count()).select_from(AttendanceRecord))
    assert attendance_count is not None
    assert attendance_count > 100

    dashboard = await api_client.get("/v1/reports/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["active_year"]["label"] == "2026-2027"
    assert body["counts"] == {"children": 24, "volunteers": 11, "classes": 4}

    years = await api_client.get("/v1/ministry-years")
    by_label = {item["label"]: item for item in years.json()["items"]}
    current_classes = await api_client.get(
        "/v1/classes",
        params={"ministry_year_id": by_label["2026-2027"]["id"]},
    )
    assert current_classes.json()["total"] == 4
    preschool = next(
        item for item in current_classes.json()["items"] if item["name"] == "Preschool"
    )
    sessions = await api_client.get(f"/v1/classes/{preschool['id']}/sessions")
    assert sessions.json()["total"] == 11

    promotion = await api_client.post(
        "/v1/promotions/preview",
        json={
            "source_year_id": by_label["2025-2026"]["id"],
            "target_year_id": by_label["2026-2027"]["id"],
            "mappings": [
                {
                    "source_class_id": next(
                        item["id"]
                        for item in (
                            await api_client.get(
                                "/v1/classes",
                                params={"ministry_year_id": by_label["2025-2026"]["id"]},
                            )
                        ).json()["items"]
                        if item["name"] == "Preschool"
                    ),
                    "target_class_id": next(
                        item["id"]
                        for item in current_classes.json()["items"]
                        if item["name"] == "Kindergarten"
                    ),
                }
            ],
        },
    )
    assert promotion.status_code == 200, promotion.text
    assert promotion.json()["counts"]["assign"] == 3
    assert promotion.json()["counts"]["already_enrolled"] > 0


async def test_seed_demo_refuses_to_run_twice(db_session: AsyncSession) -> None:
    await seed_demo(db_session)

    with pytest.raises(DemoDataExistsError):
        await seed_demo(db_session)

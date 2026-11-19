"""Audit trail contracts for personal-data mutations."""

from typing import Any

from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL
from tests.helpers import (
    create_child,
    create_class,
    create_session,
    create_year,
    enroll_child,
)


async def _logs(client: AsyncClient, *, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
    response = await client.get(
        "/v1/audit-logs",
        params={"entity_type": entity_type, "entity_id": entity_id},
    )
    assert response.status_code == 200, response.text
    return list(response.json()["items"])


async def test_child_create_and_update_are_audited(api_client: AsyncClient) -> None:
    child = await create_child(api_client)
    create_logs = await _logs(api_client, entity_type="child", entity_id=child["id"])

    assert len(create_logs) == 1
    created = create_logs[0]
    assert created["action"] == "create"
    assert created["actor_email"] == ADMIN_EMAIL
    assert created["changes"]["after"]["first_name"] == "Grace"

    updated = await api_client.patch(
        f"/v1/children/{child['id']}",
        json={"allergies": "Peanuts", "status": "inactive"},
    )
    assert updated.status_code == 200

    logs = await _logs(api_client, entity_type="child", entity_id=child["id"])
    assert len(logs) == 2
    update_log = logs[0]
    assert update_log["action"] == "update"
    changes = update_log["changes"]["changes"]
    assert changes["allergies"] == {"from": None, "to": "Peanuts"}
    assert changes["status"] == {"from": "active", "to": "inactive"}

    # Reads do not create audit records.
    await api_client.get(f"/v1/children/{child['id']}")
    assert len(await _logs(api_client, entity_type="child", entity_id=child["id"])) == 2


async def test_guardian_and_link_changes_are_audited(api_client: AsyncClient) -> None:
    child = await create_child(api_client)
    guardian_response = await api_client.post(
        "/v1/guardians",
        json={"first_name": "Mary", "last_name": "Hopper", "phone": "123"},
    )
    guardian = guardian_response.json()
    assert len(await _logs(api_client, entity_type="guardian", entity_id=guardian["id"])) == 1

    link = await api_client.post(
        f"/v1/children/{child['id']}/guardians",
        json={"guardian_id": guardian["id"], "relationship": "Mother"},
    )
    link_body = link.json()
    logs = await _logs(api_client, entity_type="child_guardian", entity_id=link_body["id"])
    assert len(logs) == 1
    assert logs[0]["changes"]["after"]["relationship"] == "Mother"

    promoted = await api_client.post(f"/v1/child-guardians/{link_body['id']}/set-primary")
    assert promoted.status_code == 200
    logs = await _logs(api_client, entity_type="child_guardian", entity_id=link_body["id"])
    assert len(logs) == 2
    assert logs[0]["changes"]["changes"]["is_primary"] == {
        "from": False,
        "to": True,
    }


async def test_attendance_bulk_update_is_audited(api_client: AsyncClient) -> None:
    year = await create_year(api_client)
    school_class = await create_class(api_client, ministry_year_id=str(year["id"]))
    child = await create_child(api_client)
    await enroll_child(api_client, class_id=str(school_class["id"]), child_id=str(child["id"]))
    session = await create_session(api_client, class_id=str(school_class["id"]))

    response = await api_client.put(
        f"/v1/class-sessions/{session['id']}/attendance",
        json={
            "records": [{"child_id": child["id"], "status": "present"}],
            "visitors": [{"name": "Visitor"}],
        },
    )
    assert response.status_code == 200

    logs = await _logs(api_client, entity_type="attendance", entity_id=session["id"])
    assert len(logs) == 1
    changes = logs[0]["changes"]
    assert changes["children"][child["id"]]["to"]["status"] == "present"
    assert changes["visitors"]["to"][0]["name"] == "Visitor"


async def test_audit_filters_and_pagination(api_client: AsyncClient) -> None:
    first = await create_child(api_client, first_name="Grace")
    await create_child(api_client, first_name="Katherine")

    by_type = await api_client.get("/v1/audit-logs", params={"entity_type": "child"})
    assert by_type.status_code == 200
    assert by_type.json()["total"] >= 2

    by_actor = await api_client.get("/v1/audit-logs", params={"action": "create"})
    assert by_actor.status_code == 200
    assert all(item["action"] == "create" for item in by_actor.json()["items"])

    by_entity = await api_client.get(
        "/v1/audit-logs",
        params={"entity_type": "child", "entity_id": first["id"]},
    )
    assert by_entity.json()["total"] == 1

    paged = await api_client.get(
        "/v1/audit-logs", params={"entity_type": "child", "limit": 1, "offset": 1}
    )
    assert paged.status_code == 200
    assert paged.json()["limit"] == 1
    assert paged.json()["offset"] == 1

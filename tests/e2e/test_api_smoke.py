"""End-to-end smoke tests against the FastAPI application."""


from fastapi.testclient import TestClient

from api.main import app


def test_healthcheck(monkeypatch, db):
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_tender(db, seed_entities):
    client = TestClient(app)
    payload = {
        "etimad_tender_id": "TEST-E2E-1",
        "title_ar": "منافسة اختبار end-to-end",
        "government_entity_id": str(seed_entities["entity"].id),
        "region_id": str(seed_entities["region"].id),
        "primary_sector_id": str(seed_entities["sector"].id),
        "award_date": "2026-05-15",
        "award_value": 1_500_000.00,
        "awarded_to_competitor_id": str(seed_entities["competitor"].id),
        "rawasi_participated": False,
        "boq_items": [
            {
                "sequence_number": "1.1",
                "original_description": "بند اختبار",
                "original_unit": "no",
                "quantity": 10,
            }
        ],
    }
    create = client.post("/tenders", json=payload)
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["etimad_tender_id"] == "TEST-E2E-1"
    tender_id = body["id"]

    listed = client.get("/tenders")
    assert listed.status_code == 200
    assert any(t["id"] == tender_id for t in listed.json())


def test_master_item_lifecycle(db):
    client = TestClient(app)
    create = client.post(
        "/master-items",
        json={
            "code": "TEST-MI-001",
            "name_ar": "بند اختبار",
            "default_unit": "no",
        },
    )
    assert create.status_code == 201
    mi_id = create.json()["id"]

    fetched = client.get(f"/master-items/{mi_id}")
    assert fetched.status_code == 200
    assert fetched.json()["code"] == "TEST-MI-001"


def test_normalize_endpoint(db, seed_master_items):
    from api.models import MasterItemSynonym

    target = seed_master_items["PAINT-INT-PLST"]
    db.add(
        MasterItemSynonym(
            master_item_id=target.id,
            synonym_text="دهان بلاستيكي داخلي درجه اولي",
            source="manual",
        )
    )
    db.commit()

    client = TestClient(app)
    response = client.post(
        "/normalize/item",
        json={
            "description": "دهان بلاستيكي داخلي درجة أولى",
            "unit": "m2",
            "use_claude": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["match_found"] is True
    assert body["master_item_code"] == "PAINT-INT-PLST"


def test_go_no_go_endpoint(db):
    client = TestClient(app)
    response = client.post(
        "/analytics/go-no-go",
        json={
            "estimated_award_value": 3_000_000,
            "expected_competitors": 5,
            "expected_margin_pct": 10.0,
            "rawasi_capacity_load_pct": 50.0,
            "relationship_with_entity": "good",
            "sector_strategic_priority": "high",
            "payment_terms_score": 0.8,
            "item_overlap_with_capacity_pct": 0.9,
            "win_probability": 0.75,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] in {"GO", "REVIEW", "NO_GO"}
    assert 0 <= body["composite_score"] <= 1


def test_win_probability_endpoint(db, seed_entities):
    client = TestClient(app)
    response = client.post(
        "/analytics/win-probability",
        json={
            "proposed_bid": 900.0,
            "scenarios": [
                {
                    "competitor_id": str(seed_entities["competitor"].id),
                    "entry_probability": 0.9,
                    "bid_low": 950.0,
                    "bid_high": 1050.0,
                }
            ],
            "iterations": 500,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["probability"] <= 1.0

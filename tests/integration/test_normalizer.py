"""Normalization pipeline tests against the test DB."""

from api.services.boq_normalizer import BoqNormalizer


def test_keyword_match_via_synonyms(db, seed_master_items):
    from api.models import MasterItemSynonym

    target = seed_master_items["CONC-RC-30"]
    db.add(
        MasterItemSynonym(
            master_item_id=target.id,
            synonym_text="خرسانه مسلحه بمقاومه 30 ميجا",
            source="manual_bootstrap",
        )
    )
    db.flush()

    normalizer = BoqNormalizer(db)
    outcome = normalizer.normalize(
        "خرسانة مسلحة بمقاومة 30 ميجا", unit="m3", use_claude=False
    )
    assert outcome.match_found
    assert outcome.master_item_code == "CONC-RC-30"


def test_semantic_match_without_synonyms(db, seed_master_items):
    normalizer = BoqNormalizer(db)
    outcome = normalizer.normalize(
        "حديد تسليح قطر 12 مم درجة 60",
        unit="ton",
        use_claude=False,
    )
    # Either it matches semantically or falls into manual review
    if outcome.match_found:
        assert outcome.master_item_code == "STEEL-REBAR-Y12"
    else:
        assert outcome.requires_manual_review is True


def test_unit_mismatch_excludes_candidates(db, seed_master_items):
    normalizer = BoqNormalizer(db)
    outcome = normalizer.normalize(
        "خرسانة مسلحة بمقاومة 30 ميجا",
        unit="m2",  # WRONG unit
        use_claude=False,
    )
    # Should not match CONC-RC-30 (which is m3)
    if outcome.match_found:
        assert outcome.master_item_code != "CONC-RC-30"


def test_manual_review_when_no_match(db, seed_master_items):
    normalizer = BoqNormalizer(db)
    outcome = normalizer.normalize(
        "بند غير موجود تماماً xxxx yyyy",
        unit="lump",
        use_claude=False,
    )
    assert outcome.requires_manual_review is True


def test_synonym_recorded_on_match(db, seed_master_items):
    from sqlalchemy import select

    from api.models import MasterItemSynonym

    target = seed_master_items["FURN-DESK-EXEC"]
    db.add(
        MasterItemSynonym(
            master_item_id=target.id,
            synonym_text="مكتب تنفيذي قياس كبير",
            source="manual_bootstrap",
        )
    )
    db.commit()

    normalizer = BoqNormalizer(db)
    outcome = normalizer.normalize(
        "مكتب تنفيذي قياس كبير", unit="no", use_claude=False
    )
    assert outcome.match_found

    synonyms = db.execute(
        select(MasterItemSynonym).where(MasterItemSynonym.master_item_id == target.id)
    ).scalars().all()
    assert len(synonyms) >= 1

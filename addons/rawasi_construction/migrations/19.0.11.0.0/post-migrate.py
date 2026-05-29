# -*- coding: utf-8 -*-
"""Post-migration 19.0.11.0.0 — ربط بنود المنافسات وبيانات رادار الترسية
بالكتالوج المرجعي تلقائياً.

يطبّق محرك المطابقة الذكية (4 مستويات) على:
- كل سجلات `rawasi.boq.item` (بنود المنافسات)
- كل سجلات `rawasi.price.intelligence` (رادار الترسية)

التشغيل في post-migrate (بعد load الموديل) ليضمن أن جداول الكتالوج
المرجعي (rawasi.reference.item, rawasi.lcgpa.code) جاهزة بكامل بياناتها.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # نتحقق أن الكتالوج المرجعي يحوي بيانات قبل البدء
    cr.execute("SELECT COUNT(*) FROM rawasi_reference_item")
    catalog_size = cr.fetchone()[0]
    if catalog_size == 0:
        _logger.warning(
            "rawasi_construction: catalog empty, skipping auto-linking. "
            "Run again after seeding."
        )
        return

    from odoo.addons.rawasi_construction.services import matching_engine
    from odoo.addons.rawasi_construction.services import spec_extractor

    # ── 1) ربط بنود المنافسات ──────────────────────────────────
    boq_items = env["rawasi.boq.item"].search([("reference_item_id", "=", False)])
    matched_boq = 0
    for item in boq_items:
        specs = spec_extractor.extract_all(item.name or "")
        ref, conf, source = matching_engine.find_match(
            env,
            original_text=item.name,
            lcgpa_raw=item.construction_code or "",
            extracted_specs=specs,
        )
        if ref:
            update = {
                "reference_item_id": ref.id,
                "reference_match_source": source,
                "reference_match_confidence": conf,
            }
            # ربط رمز LCGPA المُكتشَف لو فيه
            if item.construction_code:
                lcgpa = env["rawasi.lcgpa.code"].search(
                    [("code", "=", item.construction_code.strip())], limit=1,
                )
                if lcgpa:
                    update["lcgpa_code_id"] = lcgpa.id
            item.write(update)
            matched_boq += 1
    _logger.info(
        "rawasi_construction: linked %d/%d BOQ items to reference catalog",
        matched_boq, len(boq_items),
    )

    # ── 2) ربط بيانات رادار الترسية ─────────────────────────────
    pi_items = env["rawasi.price.intelligence"].search([("reference_item_id", "=", False)])
    matched_pi = 0
    for item in pi_items:
        specs = spec_extractor.extract_all(item.name or "")
        # رادار الترسية ما عنده construction_code مباشرة، ناخذها من boq_item_id لو فيه
        lcgpa_raw = ""
        if item.boq_item_id and item.boq_item_id.construction_code:
            lcgpa_raw = item.boq_item_id.construction_code
        ref, conf, source = matching_engine.find_match(
            env,
            original_text=item.name,
            lcgpa_raw=lcgpa_raw,
            extracted_specs=specs,
        )
        if ref:
            update = {
                "reference_item_id": ref.id,
                "reference_match_source": source,
                "reference_match_confidence": conf,
            }
            if lcgpa_raw:
                lcgpa = env["rawasi.lcgpa.code"].search(
                    [("code", "=", lcgpa_raw.strip())], limit=1,
                )
                if lcgpa:
                    update["lcgpa_code_id"] = lcgpa.id
            item.write(update)
            matched_pi += 1
    _logger.info(
        "rawasi_construction: linked %d/%d price intelligence items to catalog",
        matched_pi, len(pi_items),
    )

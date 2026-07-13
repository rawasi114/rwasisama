# -*- coding: utf-8 -*-
"""منظومة المطابقة (Matching Engine) — أربعة مستويات بالترتيب:

  المستوى ١: تطابق نصي كامل (exact_text)         ← ثقة 100%
  المستوى ٢: تطابق برمز LCGPA + كلمة مشتركة     ← ثقة 70-85%
  المستوى ٣: تطابق بنمط المواصفات               ← ثقة 55%
  المستوى ٤: تطابق دلالي عبر pgvector            ← مؤجَّل (يحتاج embeddings)

نقطة الدخول: find_match(env, original_text, lcgpa_raw=None, extracted_specs=None)
ترجع: (reference_item recordset|False, confidence float, source code)
"""
import logging

from odoo.addons.rawasi_construction.models.rawasi_item_variant import (
    normalize_for_matching,
)

_logger = logging.getLogger(__name__)


def _level_1_exact_text(env, normalized):
    if not normalized:
        return None
    variant = env["rawasi.item.variant"].sudo().search(
        [("normalized_text", "=", normalized)], limit=1,
    )
    if variant:
        return (variant.reference_item_id, 100.0, "exact_text")
    return None


def _level_2_lcgpa(env, lcgpa_raw, normalized):
    if not lcgpa_raw:
        return None
    code = lcgpa_raw.strip()
    if not code or code.lower() in ("غير محدد", "لا يوجد"):
        return None
    lcgpa = env["rawasi.lcgpa.code"].sudo().search(
        [("code", "=", code)], limit=1,
    )
    if not lcgpa or not lcgpa.reference_item_ids:
        return None
    tokens = set(normalized.split()) if normalized else set()
    best, best_overlap = None, -1
    for item in lcgpa.reference_item_ids:
        name_tokens = set(normalize_for_matching(item.approved_name or "").split())
        overlap = len(tokens & name_tokens)
        if overlap > best_overlap:
            best_overlap, best = overlap, item
    if best is None:
        return None
    conf = 85.0 if best_overlap > 0 else 70.0
    return (best, conf, "lcgpa_code")


def _level_3_spec_pattern(env, normalized, extracted_specs):
    if not extracted_specs:
        return None
    dim = extracted_specs.get("dimensions")
    if not dim:
        return None
    candidates = env["rawasi.reference.item"].sudo().search(
        [("approved_name", "ilike", dim)], limit=10,
    )
    if not candidates:
        return None
    tokens = set(normalized.split()) if normalized else set()
    best, best_overlap = None, -1
    for item in candidates:
        name_tokens = set(normalize_for_matching(item.approved_name or "").split())
        overlap = len(tokens & name_tokens)
        if overlap > best_overlap:
            best_overlap, best = overlap, item
    if best is None:
        return None
    return (best, 55.0, "spec_pattern")


def _level_4_pgvector(env, normalized):
    """تطابق دلالي — مؤجَّل (يحتاج خط embeddings)."""
    return None


def find_match(env, original_text, lcgpa_raw=None, extracted_specs=None):
    """نقطة الدخول العمومية: يشغّل المستويات الأربعة بالترتيب."""
    normalized = normalize_for_matching(original_text or "")
    for fn, args in (
        (_level_1_exact_text,    (env, normalized)),
        (_level_2_lcgpa,         (env, lcgpa_raw, normalized)),
        (_level_3_spec_pattern,  (env, normalized, extracted_specs)),
        (_level_4_pgvector,      (env, normalized)),
    ):
        result = fn(*args)
        if result:
            return result
    return (env["rawasi.reference.item"].browse(), 0.0, "none")

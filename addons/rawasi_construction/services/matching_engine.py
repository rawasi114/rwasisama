# -*- coding: utf-8 -*-
"""منظومة المطابقة الذكية — أربعة مستويات بالترتيب:

  المستوى ١: تطابق نصي كامل بعد التوحيد   ← ثقة 100%
  المستوى ٢: تطابق برمز LCGPA              ← ثقة 70-85%
  المستوى ٣: تطابق بنمط المواصفات          ← ثقة 55%
  المستوى ٤: تطابق دلالي عبر pgvector      ← ثقة متغيّرة من المسافة

إذا فشلت كل المستويات يُرجَع None ويوضع السطر في حالة «بانتظار المراجعة».

تصدير الدوال:
- find_match(env, original_text, lcgpa_raw=None, extracted_specs=None)
  → (reference_item_id, confidence, source) أو (None, 0, 'none')
"""
import logging

from odoo.addons.rawasi_construction.models.arabic_utils import normalize_text

_logger = logging.getLogger(__name__)


# ── المستوى ١ ───────────────────────────────────────────────────
def _match_exact_text(env, normalized):
    """يبحث عن variant.normalized_text مطابق تماماً → ثقة 100%."""
    if not normalized:
        return None
    variant = env["rawasi.item.variant"].sudo().search(
        [("normalized_text", "=", normalized)], limit=1,
    )
    if variant:
        return (variant.reference_item_id, 100.0, "exact_text")
    return None


# ── المستوى ٢ ───────────────────────────────────────────────────
def _match_by_lcgpa(env, lcgpa_raw, normalized):
    """يبحث عن بند مرجعي يحوي نفس رمز LCGPA + كلمات مشتركة من النص.

    ثقة 85% إن كان رمز LCGPA يتطابق وكلمة واحدة على الأقل من النص
    تظهر في approved_name، 70% إن تطابق رمز LCGPA فقط.
    """
    if not lcgpa_raw:
        return None
    lcgpa_raw = lcgpa_raw.strip()
    if not lcgpa_raw or lcgpa_raw.lower() in ("غير محدد", "لا يوجد"):
        return None
    lcgpa = env["rawasi.lcgpa.code"].sudo().search(
        [("code", "=", lcgpa_raw)], limit=1,
    )
    if not lcgpa or not lcgpa.reference_item_ids:
        return None
    # Look for token overlap with approved_name to boost confidence
    tokens = set(normalized.split()) if normalized else set()
    best = None
    best_overlap = -1
    for item in lcgpa.reference_item_ids:
        name_tokens = set(normalize_text(item.approved_name or "").split())
        overlap = len(tokens & name_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best = item
    if best is None:
        return None
    conf = 85.0 if best_overlap > 0 else 70.0
    return (best, conf, "lcgpa_code")


# ── المستوى ٣ ───────────────────────────────────────────────────
def _match_by_spec_pattern(env, normalized, extracted_specs):
    """يبحث عن بنود مرجعية تطابق نمط المواصفات (أبعاد/سماكة/قطر) المُستخلَصة.

    ثقة 55% — مبدئية، تعتمد على تطابق قيم رقمية واضحة.
    """
    if not extracted_specs:
        return None
    relevant = {k: v for k, v in extracted_specs.items() if v}
    if not relevant:
        return None
    # Build a search on related rawasi.item.specification rows
    Spec = env["rawasi.item.specification"].sudo()
    matches = {}
    for key, value in relevant.items():
        candidates = Spec.search([("spec_key", "=", key), ("spec_value", "=", value)], limit=20)
        for c in candidates:
            ref_id = c.reference_item_id.id
            matches.setdefault(ref_id, 0)
            matches[ref_id] += 1
    if not matches:
        return None
    best_ref_id, _ = max(matches.items(), key=lambda kv: kv[1])
    item = env["rawasi.reference.item"].sudo().browse(best_ref_id)
    return (item, 55.0, "spec_pattern")


# ── المستوى ٤ ───────────────────────────────────────────────────
def _match_by_pgvector(env, normalized):
    """تطابق دلالي عبر pgvector — يتطلّب توفّر embeddings.

    في هذه المرحلة embeddings فارغة، فالدالة ترجع None حتى يُفعَّل خط
    توليد التضمينات في مرحلة لاحقة من خارطة الطريق.
    """
    if not normalized:
        return None
    # TODO: build embedding for `normalized` via external service, then:
    #   SELECT id, embedding <=> %s AS dist FROM rawasi_reference_item
    #   WHERE embedding IS NOT NULL ORDER BY dist LIMIT 1
    # Skipped — embeddings pipeline not wired yet.
    return None


# ── نقطة الدخول العمومية ────────────────────────────────────────
def find_match(env, original_text, lcgpa_raw=None, extracted_specs=None):
    """يشغّل المستويات الأربعة بالترتيب ويرجع أول ترشيح ينجح.

    Returns: tuple of (reference_item recordset|False, confidence float 0-100,
    source code string from selection on import.raw.line.suggestion_source).
    """
    normalized = normalize_text(original_text or "")

    for level_fn, args in (
        (_match_exact_text,    (env, normalized)),
        (_match_by_lcgpa,      (env, lcgpa_raw, normalized)),
        (_match_by_spec_pattern,(env, normalized, extracted_specs)),
        (_match_by_pgvector,   (env, normalized)),
    ):
        result = level_fn(*args)
        if result:
            ref, conf, src = result
            _logger.debug(
                "matched %r → %s (conf=%.1f, source=%s)",
                original_text[:40], ref.reference_code, conf, src,
            )
            return ref, conf, src
    return env["rawasi.reference.item"].browse(), 0.0, "none"

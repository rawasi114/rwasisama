"""BoQ item normalization service.

Implements the four-stage hybrid normalization pipeline from spec section 6:

1. Keyword / synonym match.
2. Semantic match via embeddings (pgvector in prod, cosine fallback in tests).
3. Claude-assisted disambiguation between top semantic candidates.
4. Manual-review queue for items that fall below all thresholds.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.core.config import Settings, get_settings
from api.core.logging import get_logger
from api.models import MasterItem, MasterItemSynonym
from api.utils.arabic import normalize_arabic, normalize_unit, units_compatible
from api.utils.embeddings import cosine_similarity, generate_embedding

LOG = get_logger(__name__)


@dataclass
class MatchCandidate:
    master_item_id: UUID
    master_item_code: str
    master_item_name_ar: str
    default_unit: str
    similarity: float


@dataclass
class NormalizationOutcome:
    match_found: bool
    master_item_id: UUID | None = None
    master_item_code: str | None = None
    confidence: float = 0.0
    method: str = "none"
    requires_manual_review: bool = False
    top_candidates: list[MatchCandidate] = field(default_factory=list)
    reasoning: str | None = None


class BoqNormalizer:
    """Normalizes free-text BoQ descriptions to master items."""

    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        claude_extractor=None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.claude = claude_extractor

    def normalize(
        self,
        description: str,
        unit: str | None = None,
        *,
        use_claude: bool = True,
    ) -> NormalizationOutcome:
        """Run the four-stage normalization pipeline."""
        unit_norm = normalize_unit(unit) if unit else None

        # Stage 1: keyword / synonym match
        outcome = self._keyword_match(description, unit_norm)
        if outcome.match_found and outcome.confidence >= self.settings.normalization_keyword_threshold:
            self._record_synonym(outcome.master_item_id, description, source="auto_keyword")
            return outcome

        # Stage 2: semantic match
        semantic = self._semantic_match(description, unit_norm)
        if (
            semantic.match_found
            and semantic.confidence >= self.settings.normalization_semantic_threshold
        ):
            self._record_synonym(semantic.master_item_id, description, source="auto_semantic")
            return semantic

        # Stage 3: Claude (only if enabled and candidates exist)
        if use_claude and self.claude is not None and semantic.top_candidates:
            try:
                claude_outcome = self._claude_match(description, unit_norm or "", semantic.top_candidates)
                if (
                    claude_outcome.match_found
                    and claude_outcome.confidence >= self.settings.normalization_claude_threshold
                ):
                    self._record_synonym(
                        claude_outcome.master_item_id,
                        description,
                        source="claude_extracted",
                    )
                    return claude_outcome
            except Exception as exc:  # pragma: no cover
                LOG.warning("claude_normalize_failed", error=str(exc))

        # Stage 4: manual review queue
        semantic.requires_manual_review = True
        semantic.method = "pending_manual"
        return semantic

    def _keyword_match(self, description: str, unit_norm: str | None) -> NormalizationOutcome:
        normalized = normalize_arabic(description)
        if not normalized:
            return NormalizationOutcome(match_found=False)

        synonyms = self.db.execute(
            select(MasterItemSynonym, MasterItem)
            .join(MasterItem, MasterItem.id == MasterItemSynonym.master_item_id)
            .where(MasterItem.is_active.is_(True))
        ).all()

        best: tuple[float, MasterItem] | None = None
        for synonym, master_item in synonyms:
            if unit_norm and not units_compatible(master_item.default_unit, unit_norm):
                if not master_item.alternative_units or unit_norm not in {
                    normalize_unit(u) for u in master_item.alternative_units
                }:
                    continue
            score = _token_similarity(normalized, normalize_arabic(synonym.synonym_text))
            if best is None or score > best[0]:
                best = (score, master_item)

        if best is None:
            return NormalizationOutcome(match_found=False)

        score, mi = best
        return NormalizationOutcome(
            match_found=score >= self.settings.normalization_keyword_threshold,
            master_item_id=mi.id,
            master_item_code=mi.code,
            confidence=score,
            method="keyword",
            top_candidates=[
                MatchCandidate(
                    master_item_id=mi.id,
                    master_item_code=mi.code,
                    master_item_name_ar=mi.name_ar,
                    default_unit=mi.default_unit,
                    similarity=score,
                )
            ],
        )

    def _semantic_match(self, description: str, unit_norm: str | None) -> NormalizationOutcome:
        query_vec = generate_embedding(description)
        candidates = self.db.execute(
            select(MasterItem).where(MasterItem.is_active.is_(True))
        ).scalars().all()

        scored: list[MatchCandidate] = []
        for mi in candidates:
            if unit_norm and not units_compatible(mi.default_unit, unit_norm):
                if not mi.alternative_units or unit_norm not in {
                    normalize_unit(u) for u in mi.alternative_units
                }:
                    continue
            item_vec = self._get_or_compute_embedding(mi)
            if item_vec is None:
                continue
            sim = cosine_similarity(query_vec, item_vec)
            scored.append(
                MatchCandidate(
                    master_item_id=mi.id,
                    master_item_code=mi.code,
                    master_item_name_ar=mi.name_ar,
                    default_unit=mi.default_unit,
                    similarity=sim,
                )
            )

        scored.sort(key=lambda c: c.similarity, reverse=True)
        top = scored[:5]
        if not top:
            return NormalizationOutcome(match_found=False, method="semantic_failed")

        best = top[0]
        match_found = best.similarity >= self.settings.normalization_semantic_threshold
        return NormalizationOutcome(
            match_found=match_found,
            master_item_id=best.master_item_id if match_found else None,
            master_item_code=best.master_item_code if match_found else None,
            confidence=best.similarity,
            method="semantic" if match_found else "semantic_below_threshold",
            top_candidates=top,
        )

    def _claude_match(
        self,
        description: str,
        unit: str,
        candidates: Sequence[MatchCandidate],
    ) -> NormalizationOutcome:
        candidate_payload = [
            {
                "code": c.master_item_code,
                "name_ar": c.master_item_name_ar,
                "description_ar": "",
                "default_unit": c.default_unit,
            }
            for c in candidates
        ]
        response = self.claude.normalize_item(description, unit, candidate_payload)
        if not response.get("match_found"):
            return NormalizationOutcome(
                match_found=False,
                method="claude_no_match",
                reasoning=response.get("reasoning"),
                top_candidates=list(candidates),
            )

        selected_code = response["selected_master_code"]
        mi = self.db.execute(
            select(MasterItem).where(MasterItem.code == selected_code)
        ).scalar_one_or_none()
        if mi is None:
            return NormalizationOutcome(
                match_found=False,
                method="claude_invalid_code",
                reasoning=f"Claude returned unknown code: {selected_code}",
                top_candidates=list(candidates),
            )

        return NormalizationOutcome(
            match_found=True,
            master_item_id=mi.id,
            master_item_code=mi.code,
            confidence=float(response.get("confidence", 0.0)),
            method="claude",
            reasoning=response.get("reasoning"),
            top_candidates=list(candidates),
        )

    def _record_synonym(
        self, master_item_id: UUID | None, synonym_text: str, source: str
    ) -> None:
        if master_item_id is None:
            return
        normalized = normalize_arabic(synonym_text)
        if not normalized:
            return
        existing = self.db.execute(
            select(MasterItemSynonym).where(
                MasterItemSynonym.master_item_id == master_item_id,
                func.lower(MasterItemSynonym.synonym_text) == normalized,
            )
        ).scalar_one_or_none()
        if existing:
            existing.occurrence_count = (existing.occurrence_count or 0) + 1
            existing.last_seen_date = date.today()
        else:
            self.db.add(
                MasterItemSynonym(
                    master_item_id=master_item_id,
                    synonym_text=normalized,
                    source=source,
                    occurrence_count=1,
                    last_seen_date=date.today(),
                )
            )
        self.db.flush()

    @staticmethod
    def _get_or_compute_embedding(mi: MasterItem) -> list[float] | None:
        embedding = mi.embedding
        if embedding is None:
            return generate_embedding(f"{mi.name_ar} {mi.description_ar or ''}")
        if isinstance(embedding, (list, tuple)):
            return list(embedding)
        try:
            return list(embedding)
        except TypeError:
            return None


def _token_similarity(a: str, b: str) -> float:
    """Symmetric Jaccard-like score over token sets, biased to substring overlap."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = tokens_a & tokens_b
    if not overlap:
        return 0.0
    jaccard = len(overlap) / len(tokens_a | tokens_b)
    if a in b or b in a:
        jaccard = max(jaccard, 0.95)
    return jaccard

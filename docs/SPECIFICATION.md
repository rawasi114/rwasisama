# Award Radar (رادار الترسية) — Technical Specification (Concise)

This is the implementer-facing summary. The full strategic specification
(in Arabic) is the document of record.

## Layers

1. **Ingestion** — manual entry, Claude-assisted, Excel bulk import.
2. **Normalization** — keyword → semantic → Claude → manual review.
3. **Storage** — PostgreSQL 16 + pgvector (19 tables).
4. **Analytics** — 4 engines (Reference, Go/No-Go, Competitor, Win-Prob).
5. **UI** — Odoo module + dashboards.

## Engines

### 1. Reference Pricing
Given a master item id and context (sector, region, entity, date range),
returns weighted statistics of historical unit prices: mean, median, P25,
P75, std, observation count, and a recommended price for Rawasi.

### 2. Go/No-Go
Composite scoring on six factors with documented weights:
- Win probability (30%)
- Expected margin (25%)
- Strategic value (15%)
- Capacity match (10%)
- Effort required (10%)
- Cash flow impact (10%)

Decision thresholds:
- ≥ 0.65 → GO
- 0.45–0.64 → REVIEW
- < 0.45 → NO_GO

### 3. Competitor Profile
Per-competitor analysis over a configurable window (default 24 months):
appearances, wins, win rate, value distributions, sector/region/entity
distributions, threat score (1–100), predicted appearance categories.

### 4. Win Probability
Monte-Carlo simulation (default 10k iterations) over competitor entry
scenarios, returning win probability + confidence + sensitivity curve.
Also implements `find_optimal_bid` which maximizes expected value
(`probability × margin × bid`).

## Reverse Price Allocation

Distribute the awarded value `V` across BoQ items so that
`sum(unit_price * quantity) == V` exactly while respecting:
- reference price per master item
- category-aware discount weights (commodities take deeper cuts)
- a global discount factor `d = V / market_total`

Invariant enforced by `PriceAllocator.allocate`: the resulting sum must
match `V` within 1 SAR or `AllocationError` is raised.

## Normalization Pipeline

1. **Keyword** — synonym table lookup (Jaccard token overlap, threshold 0.90).
2. **Semantic** — embedding cosine similarity over `master_items` (threshold 0.85).
3. **Claude** — disambiguation between top-5 semantic candidates (threshold 0.75).
4. **Manual review** — anything below all thresholds flagged for human review.

Successful matches automatically record the original text as a new synonym,
making the system smarter with every use.

## Data Quality

- Required fields enforced at the schema layer (Pydantic).
- Date logic (publication ≤ submission ≤ award) enforced in the service.
- Anomaly check on award value vs sector mean (warn if deviation ≥ 80%).
- Weekly automated report (planned).

## Deployment

- **dev:** `claude/intelligent-carson-SAFBz` — automated tests on PR.
- **staging:** `staging` branch — full pipeline + manual smoke tests.
- **production:** `main` branch — protected, requires green CI + manual approval.

See `docs/DEPLOYMENT.md` for the runbook.

# PLAN.md — Rawasi Item Catalog Module

**Branch:** `claude/item-catalog` (forked from `main`)
**Target Module:** `addons/rawasi_item_catalog/`
**Target Odoo:** 19 (adapted from SPEC's 17/18)
**Status:** ⏸ Pending CEO approval before any code is written

---

## 0. Environment Discovery Findings

| Item | SPEC Assumption | Actual Reality | Decision |
|---|---|---|---|
| Parent module | `rawasi_pricing_intelligence` | Renamed to `rawasi_construction` in commit `b0a8586` | Build catalog as standalone — no parent dependency |
| Odoo version | 17 or 18 | **19** | Use Odoo 19 idioms (`models.Constraint`, `_compute_in_new_api`, etc.) |
| `master_item.py` | Exists, conflict-check needed | **Does not exist** | No naming conflict |
| Closest existing model | — | `rawasi.boq.item` (per-tender BOQ rows) | Conceptually distinct from canonical catalog → no overlap |
| Branch base | `main` or `develop` | `main` (essentially empty: only initial commit) | Forked from `main` ✓ |
| Staging DB | `rawasi_staging` | Odoo.sh staging on `Test` branch | Deploy by merging `claude/item-catalog` → `Test` |
| `.env.staging` | Required | Not used in Odoo.sh workflow | Skip — secrets via Odoo.sh env panel if needed |
| pgvector status | Verify | **Cannot verify without DB shell** | Will verify in Phase 0 via Odoo.sh webshell |

**Key insight:** The catalog is genuinely a new layer. It does NOT replace `rawasi.boq.item` — it provides a canonical lookup target so that future BOQ rows can carry a `canonical_item_id` (deferred to a later phase per CEO answer).

---

## 1. Phase Breakdown — Atomic Task List

### Phase 0 — Module Skeleton + Environment Verification
**Goal:** A module that installs (does nothing yet) + verified pgvector.

| # | Task | Est. |
|---|---|---|
| 0.1 | Create `addons/rawasi_item_catalog/` directory tree per SPEC §3 | 10m |
| 0.2 | Write `__manifest__.py` (Odoo 19, depends: base/mail/uom) | 10m |
| 0.3 | Write empty `__init__.py` files (models, services, tests) | 5m |
| 0.4 | Write placeholder `README.md` + `CHANGELOG.md` | 10m |
| 0.5 | Verify pgvector on Odoo.sh staging via webshell + document outcome | 15m |
| 0.6 | Write `migrations/19.0.1.0.0/pre-init.py` (CREATE EXTENSION vector) | 10m |
| 0.7 | Write `PHASE_0_REPORT.md` (Arabic + English) | 20m |
| 0.8 | Push to `claude/item-catalog`, do NOT merge | 5m |
| **🛑** | **STOP — wait for CEO approval** | — |

**Phase 0 Deliverable:** Module installs cleanly on `Test` (staging) but has no UI, no business logic.

### Phase 1 — Core Models + Security + Seed
**Goal:** Five models fully defined, install creates tables, 5 divisions seeded, no UI yet.

| # | Task | Est. |
|---|---|---|
| 1.1 | `models/item_taxonomy.py` — `rawasi.item.taxonomy` with `_parent_store`, hierarchy constraint | 1.5h |
| 1.2 | `models/item_master.py` — `rawasi.item.master` with canonical-code regex constraint | 2h |
| 1.3 | `models/item_synonym.py` — `rawasi.item.synonym` with `_compute_normalized` (Arabic-aware) | 1.5h |
| 1.4 | `models/item_attribute.py` — `rawasi.item.attribute` | 45m |
| 1.5 | `models/item_mapping_audit.py` — `rawasi.item.mapping.audit` | 45m |
| 1.6 | `security/security.xml` — 3 groups (user/editor/admin) | 30m |
| 1.7 | `security/ir.model.access.csv` — 5 models × 3 groups = 15 lines | 30m |
| 1.8 | `data/taxonomy_root_seed.xml` — 5 divisions per SPEC §6.1 | 20m |
| 1.9 | `migrations/19.0.1.0.0/post-init.py` — embedding columns + HNSW indexes (1024-dim) | 45m |
| 1.10 | Smoke install on local dev (or staging) — verify no errors | 30m |
| 1.11 | Write `PHASE_1_REPORT.md` | 30m |
| **🛑** | **STOP — wait for CEO approval** | — |

### Phase 2 — Views & UX
**Goal:** Operable in Odoo UI; CRUD works for all 5 models.

| # | Task | Est. |
|---|---|---|
| 2.1 | `views/item_taxonomy_views.xml` — tree, form, kanban, hierarchy, search | 1.5h |
| 2.2 | `views/item_master_views.xml` — tree, form (with attribute/synonym tabs), search | 2h |
| 2.3 | `views/item_synonym_views.xml` — tree, form, search with frequency/date filters | 45m |
| 2.4 | `views/item_attribute_views.xml` — inline list within master form | 30m |
| 2.5 | `views/item_mapping_audit_views.xml` — tree, form (read-mostly), search | 45m |
| 2.6 | `views/menu.xml` — root menu + 4 submenus, security-gated | 30m |
| 2.7 | Smoke UX walkthrough — navigate, create, edit, delete every model | 30m |
| 2.8 | Write `PHASE_2_REPORT.md` with screenshots from staging | 1h |
| **🛑** | **STOP — wait for CEO approval** | — |

### Phase 3 — Tests, Docs, Claude Stub
**Goal:** ≥80% coverage, all tests green, module is releasable.

| # | Task | Est. |
|---|---|---|
| 3.1 | `tests/test_taxonomy.py` — hierarchy constraint, parent_path, code uniqueness (≥8 tests) | 1.5h |
| 3.2 | `tests/test_master_item.py` — code-regex, taxonomy domain, CRUD, synonym count compute (≥10) | 2h |
| 3.3 | `tests/test_synonym.py` — normalization (diacritics, whitespace, digits AR/EN), uniqueness (≥6) | 1.5h |
| 3.4 | `tests/test_mapping_audit.py` — append-only semantics, CRUD (≥4) | 45m |
| 3.5 | `tests/test_pgvector.py` — extension presence, column dim, HNSW index, cosine query smoke (≥3) | 1h |
| 3.6 | `services/claude_canonicalizer.py` — stub per SPEC §8 + `health_check()` | 30m |
| 3.7 | `i18n/ar.po` — translations for non-translate strings | 45m |
| 3.8 | `README.md` final + `CHANGELOG.md` for 1.0.0 | 45m |
| 3.9 | Code coverage report (target ≥80%) | 30m |
| 3.10 | Write `PHASE_3_REPORT.md` with full test results + coverage | 45m |
| **🛑** | **STOP — wait for CEO final approval to merge** | — |

---

## 2. Risks Identified

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | pgvector not installed on Odoo.sh staging — Odoo.sh may not allow `CREATE EXTENSION` from a migration without superuser | High | Module install fails | Verify in Phase 0 via webshell. If blocked, escalate to Odoo.sh support OR make embedding column optional (gated `try/except`) |
| R2 | Production restored from backup is in a fragile state right after the `finance_user_id` incident | Medium | Risk of further instability if I rush | Keep all work on `claude/item-catalog`. Do NOT push to `Test` or `rawasisama` until CEO greenlight. Stabilize production first |
| R3 | Odoo 19 syntax changes vs SPEC's 17/18 assumptions (e.g. `_sql_constraints` deprecated → `models.Constraint`) | Certain | Code style drift | I'll use Odoo 19 idioms (already applied in `rawasi_construction`'s recent cleanup commits) |
| R4 | Arabic normalization (synonym `_compute_normalized`) is non-trivial — diacritics + tatweel + digit folding + alef variants | High | Wrong synonym matches | Build normalization as pure function with unit tests. Use Unicode NFKD + explicit Arabic mapping (no half-built shortcuts) |
| R5 | `tax_div_inhouse` (in-house manufacturing) overlaps conceptually with `is_in_house` flag on `rawasi.item.master` | Low | Confusion | Document clearly: taxonomy categorizes WHAT, flag categorizes WHO MAKES IT. They can disagree (e.g. an item in ELEC division can still be `is_in_house=True`) |
| R6 | SPEC mandates 1024-dim embedding column but no embedding model is wired yet | Low | NULL embeddings = no semantic search until Phase 2 of catalog rollout | Acceptable per SPEC §5.3 — column is reserved, population deferred |
| R7 | CEO has not specified which Odoo.sh build env policy to use for staging (network egress for future Claude API) | Low | Will block Phase 2 of catalog rollout, not this work | Defer — Claude integration is out of scope per SPEC §0.3 |

---

## 3. Open Questions Before Phase 0

1. **pgvector verification:** Should I (a) run `psql` via Odoo.sh staging webshell myself to confirm extension status now, or (b) wait for you to do it and report back?
2. **Branch naming:** SPEC says `feature/master-item-catalog`. I used `claude/item-catalog` (matches the `claude/*` convention in our repo). OK?
3. **Module icon:** SPEC §3 lists `static/description/icon.png`. Should I generate a simple placeholder, or skip until you provide art?
4. **Coverage tooling:** Odoo.sh test runner doesn't expose coverage natively. Should I (a) report coverage via local pytest run only, or (b) wire coverage.py into CI in Phase 3?
5. **Production restoration check:** Has the backup restore on production stabilized things? If you'd rather I diagnose the `finance_user_id` orphan first, I'll switch to that and pause this work.

---

## 4. Forbidden in This Round (per SPEC §13)

- ❌ Writing any Python file in `rawasi_item_catalog`
- ❌ Modifying anything in `addons/rawasi_construction` or `rwasi_workshop`
- ❌ Touching `main`, `Test`, or `rawasisama` branches
- ❌ Installing the module anywhere
- ❌ Assuming an answer to any of the 5 questions above

---

## 5. Time Estimate (Total)

| Phase | Estimate |
|---|---|
| Phase 0 | ~1.5 hours |
| Phase 1 | ~8.5 hours |
| Phase 2 | ~7.5 hours |
| Phase 3 | ~10 hours |
| **Total** | **~27.5 hours** of focused build time, plus gate-wait time between phases |

---

## 6. Acceptance Trace (How to verify each SPEC §12 criterion)

| §12 Criterion | Verification Step |
|---|---|
| Module installs without error on staging | Phase 1 end — push, observe Odoo.sh build green |
| 5 models visible in UI | Phase 2 end — manual walkthrough |
| 5 divisions seeded | Phase 1 end — view `rawasi.item.taxonomy` in shell or UI |
| pgvector + HNSW indexes | Phase 1 end — `\d rawasi_item_master` in psql |
| All constraints work | Phase 3 — automated tests cover each constraint |
| CRUD on all 5 models | Phase 3 — `test_*.py` files |
| 100% test pass rate | Phase 3 end — pytest output |
| ≥80% coverage | Phase 3 end — coverage report |
| Zero server errors | Every phase — Odoo.sh logs sweep |
| Clean uninstall | Phase 3 — `odoo-bin -u rawasi_item_catalog --uninstall` |
| Production untouched | Branch isolation — `claude/item-catalog` never pushed to `rawasisama` until CEO greenlight |
| No secrets in repo | Git hook + grep audit before each push |

---

🛑 **Awaiting CEO approval of this PLAN.md before starting Phase 0.**

If approved as-is, reply: **"وافقت — ابدأ Phase 0"**.
If changes needed, point to the section/row and I'll revise without starting code.

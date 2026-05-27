# Seed Data

This directory holds the static reference data used to bootstrap a fresh
database. To load it:

```bash
python -m scripts.seed_reference_data
```

The script is idempotent — it inserts rows that don't yet exist and
leaves existing rows untouched.

## Files

- `excel_import_template.xlsx` — the standard template the data-entry
  team uses for bulk historical imports.

## Updating Reference Data

The Python data lives in `scripts/seed_reference_data.py` so it is
version-controlled with the rest of the codebase. To add a new region,
sector, or government entity:

1. Edit the relevant Python list.
2. Open a PR.
3. After merge to `staging` the deploy script re-runs the seed function.

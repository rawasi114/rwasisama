from . import models
from . import services


def _pre_init_hook(env):
    """Ensure pgvector is available before any tables are created.

    Manifest-level hook runs on both fresh install and upgrade, unlike
    the migrations/<version>/pre-init.py which only fires on upgrade.
    Fails loudly with a Postgres error if the extension is not present
    and the role can't create it — that's the signal that pgvector must
    be enabled out-of-band on the Postgres instance.
    """
    env.cr.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def _post_init_hook(env):
    """Add 1024-dim embedding columns + HNSW cosine indexes after install.

    Done in raw SQL because Odoo's ORM has no native vector field. The
    columns stay NULL until the (out-of-scope-for-this-module) embedding
    pipeline starts populating them. HNSW index on an empty column is
    cheap; it grows as rows are filled.
    """
    queries = [
        "ALTER TABLE rawasi_item_master "
        "ADD COLUMN IF NOT EXISTS embedding vector(1024)",
        "CREATE INDEX IF NOT EXISTS rawasi_item_master_embedding_idx "
        "ON rawasi_item_master USING hnsw (embedding vector_cosine_ops)",
        "ALTER TABLE rawasi_item_synonym "
        "ADD COLUMN IF NOT EXISTS embedding vector(1024)",
        "CREATE INDEX IF NOT EXISTS rawasi_item_synonym_embedding_idx "
        "ON rawasi_item_synonym USING hnsw (embedding vector_cosine_ops)",
    ]
    for q in queries:
        env.cr.execute(q)

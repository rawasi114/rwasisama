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
    """Post-install setup: pgvector columns + bootstrap admin access.

    1. Add 1024-dim embedding columns + HNSW cosine indexes via raw SQL
       (Odoo ORM has no native vector field). The columns stay NULL until
       the embedding pipeline (out of scope here) starts populating them.

    2. Grant the admin user the catalog admin group so the App Launcher
       icon is reachable immediately after install. Without this, the
       module installs cleanly but the menu — which is groups-gated — is
       invisible to everyone, and the user thinks the install failed.
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

    admin_group = env.ref(
        "rawasi_item_catalog.group_item_catalog_admin", raise_if_not_found=False,
    )
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if admin_group and admin_user:
        admin_group.write({"user_ids": [(4, admin_user.id)]})

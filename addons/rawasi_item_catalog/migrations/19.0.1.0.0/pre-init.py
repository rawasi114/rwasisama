# -*- coding: utf-8 -*-
"""Pre-install hook: ensure pgvector extension is available.

CREATE EXTENSION requires the role running Odoo to have appropriate
privileges (superuser on most managed Postgres setups). On Odoo.sh the
default db role can create extensions in its own database, so this
should succeed on install. If it does not, the install fails fast with
a clear Postgres error and we know pgvector must be enabled out-of-band.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("rawasi_item_catalog: ensuring pgvector extension is available")
    cr.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cr.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
    row = cr.fetchone()
    if row:
        _logger.info("rawasi_item_catalog: pgvector %s ready", row[0])
    else:
        _logger.warning("rawasi_item_catalog: pgvector extension not detected after CREATE")

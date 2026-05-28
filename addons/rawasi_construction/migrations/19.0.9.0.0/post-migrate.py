# -*- coding: utf-8 -*-
"""بعد تحديث Odoo: إنشاء أعمدة embedding للبحث الدلالي + ضمان صلاحية admin
على مجموعات الكتالوج.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # أعمدة pgvector + فهارس HNSW
    for q in [
        "ALTER TABLE rawasi_item_master "
        "ADD COLUMN IF NOT EXISTS embedding vector(1024)",
        "CREATE INDEX IF NOT EXISTS rawasi_item_master_embedding_idx "
        "ON rawasi_item_master USING hnsw (embedding vector_cosine_ops)",
        "ALTER TABLE rawasi_item_synonym "
        "ADD COLUMN IF NOT EXISTS embedding vector(1024)",
        "CREATE INDEX IF NOT EXISTS rawasi_item_synonym_embedding_idx "
        "ON rawasi_item_synonym USING hnsw (embedding vector_cosine_ops)",
    ]:
        cr.execute(q)
    _logger.info("rawasi_construction: embedding columns + HNSW indexes ready")

    # ضمان صلاحية admin على مجموعة مدير الكتالوج
    env = api.Environment(cr, SUPERUSER_ID, {})
    admin_group = env.ref(
        "rawasi_construction.group_item_catalog_admin", raise_if_not_found=False,
    )
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if admin_group and admin_user:
        admin_group.write({"user_ids": [(4, admin_user.id)]})

# -*- coding: utf-8 -*-
from . import models
from . import wizards


def _pre_init_hook(env):
    """قبل تحميل أي شيء — تفعيل امتداد pgvector + إعادة ملكية بيانات
    موديول rawasi_item_catalog المنفصل (السابق) إلى rawasi_construction
    حتى تبقى الـ 519 بنداً المعيارية + شجرة التصنيف + المرادفات سليمة بعد الدمج.
    """
    env.cr.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    # نقل الملكية: كل سجل ir.model.data كان مملوكاً للموديول المنفصل يصبح
    # مملوكاً لـ rawasi_construction. هذا يحمي البنود من الحذف عند إلغاء
    # تثبيت rawasi_item_catalog، ويسمح لملفات data بإيجاد السجلات الموجودة.
    env.cr.execute("""
        UPDATE ir_model_data
        SET module = 'rawasi_construction'
        WHERE module = 'rawasi_item_catalog'
    """)


def _post_init_hook(env):
    """بعد التحميل: إنشاء أعمدة embedding للبحث الدلالي + ضمان صلاحيات admin
    على مجموعات الكتالوج لظهور القوائم.
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
        "rawasi_construction.group_item_catalog_admin",
        raise_if_not_found=False,
    )
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if admin_group and admin_user:
        admin_group.write({"user_ids": [(4, admin_user.id)]})

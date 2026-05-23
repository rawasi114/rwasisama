# -*- coding: utf-8 -*-
"""يفعّل توليد أوامر التصنيع تلقائياً للشركات التي تحوي "رواسي" في اسمها."""


def _normalize(text):
    if not text:
        return ""
    return text.replace("ى", "ي").strip().lower()


def migrate(cr, version):
    cr.execute("SELECT id, name FROM res_company")
    for company_id, name in cr.fetchall():
        is_rawasi = "رواسي" in _normalize(name)
        cr.execute(
            "UPDATE res_company SET workshop_auto_mo = %s WHERE id = %s",
            (is_rawasi, company_id),
        )

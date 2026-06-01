# -*- coding: utf-8 -*-
import logging

from odoo import models


_logger = logging.getLogger(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _register_hook(self):
        result = super()._register_hook()
        try:
            self._rawasi_apply_technical_office_menu_split()
        except Exception:
            _logger.exception("Failed to apply Rawasi technical office menu split")
        return result

    def _rawasi_apply_technical_office_menu_split(self):
        env = self.env
        Menu = env["ir.ui.menu"].sudo()
        ModelData = env["ir.model.data"].sudo()
        module = "rawasi_construction"

        def ref(xmlid):
            record = env.ref(xmlid, raise_if_not_found=False)
            if record and record.exists():
                return record.sudo()
            return Menu.browse()

        def bind_xmlid(name, record):
            data = ModelData.search([("module", "=", module), ("name", "=", name)], limit=1)
            values = {
                "module": module,
                "name": name,
                "model": "ir.ui.menu",
                "res_id": record.id,
                "noupdate": False,
            }
            if data:
                if data.model != "ir.ui.menu" or data.res_id != record.id:
                    data.write(values)
            else:
                ModelData.create(values)

        def group_ids(xmlids):
            groups = []
            for xmlid in xmlids:
                group = ref(xmlid)
                if group:
                    groups.append(group.id)
            return groups

        tech_groups = group_ids(
            [
                "rawasi_construction.group_tech_office_manager",
                "rawasi_construction.group_projects_director",
                "rawasi_construction.group_ceo",
            ]
        )

        def ensure_menu(xmlid_name, values, fallback_domain=None):
            menu = ref(f"{module}.{xmlid_name}")
            if not menu and fallback_domain:
                menu = Menu.search(fallback_domain, limit=1)
                if menu:
                    bind_xmlid(xmlid_name, menu)
            if menu:
                menu.write(values)
                return menu

            create_values = dict(values)
            menu = Menu.create(create_values)
            bind_xmlid(xmlid_name, menu)
            return menu

        execution_root = ref("rawasi_construction.menu_rawasi_root")
        if not execution_root:
            return

        execution_root.write({"name": "المقاولات والتنفيذ", "sequence": 10, "active": True})

        technical_root = ensure_menu(
            "menu_rawasi_technical_office_root",
            {
                "name": "المكتب الفني - التسعير والحصر",
                "parent_id": False,
                "web_icon": "rawasi_construction,static/description/icon.png",
                "sequence": 8,
                "active": True,
                "groups_id": [(6, 0, tech_groups)],
            },
            [("parent_id", "=", False), ("name", "ilike", "المكتب الفني")],
        )

        pricing_menu = ensure_menu(
            "menu_rawasi_pricing_analysis",
            {
                "name": "تحليل الأسعار",
                "parent_id": technical_root.id,
                "sequence": 30,
                "active": True,
            },
            [("parent_id", "=", technical_root.id), ("name", "ilike", "تحليل الأسعار")],
        )

        technical_config = ensure_menu(
            "menu_rawasi_technical_office_config",
            {
                "name": "إعدادات المكتب الفني",
                "parent_id": technical_root.id,
                "sequence": 90,
                "active": True,
                "groups_id": [(6, 0, tech_groups)],
            },
            [("parent_id", "=", technical_root.id), ("name", "ilike", "إعدادات المكتب الفني")],
        )

        moves = {
            "menu_rawasi_competitions": {
                "name": "الدراسات والمنافسات",
                "parent_id": technical_root.id,
                "sequence": 10,
                "active": True,
            },
            "menu_rawasi_reference_registry_root": {
                "name": "الحصر وسجل البنود",
                "parent_id": technical_root.id,
                "sequence": 20,
                "active": True,
            },
            "menu_dash_competition": {
                "name": "تحليل المنافسات",
                "parent_id": pricing_menu.id,
                "sequence": 10,
                "active": True,
            },
            "menu_rawasi_price_intelligence": {
                "name": "ذاكرة الأسعار / رادار الترسية",
                "parent_id": pricing_menu.id,
                "sequence": 20,
                "active": True,
            },
            "menu_rawasi_units": {
                "name": "وحدات القياس",
                "parent_id": technical_config.id,
                "sequence": 10,
                "active": True,
            },
            "menu_rawasi_sbc": {
                "name": "رموز كود البناء (SBC)",
                "parent_id": technical_config.id,
                "sequence": 20,
                "active": True,
            },
        }
        for xmlid_name, values in moves.items():
            menu = ref(f"{module}.{xmlid_name}")
            if menu:
                menu.write(values)

        for xmlid in (
            "rawasi_competitions.menu_rawasi_competitions_root",
            "rawasi_competitions.menu_competitions_pricing_root_dashboard",
        ):
            old_menu = ref(xmlid)
            if old_menu:
                old_menu.write({"active": False})

        _logger.info("Applied Rawasi technical office menu split")

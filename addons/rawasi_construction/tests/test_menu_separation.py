# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMenuSeparation(TransactionCase):
    def test_technical_office_menus_are_separate(self):
        tech_root = self.env.ref("rawasi_construction.menu_rawasi_technical_office_root")

        for xmlid in (
            "rawasi_construction.menu_rawasi_competitions",
            "rawasi_construction.menu_rawasi_reference_registry_root",
            "rawasi_construction.menu_rawasi_pricing_analysis",
            "rawasi_construction.menu_rawasi_technical_office_config",
        ):
            menu = self.env.ref(xmlid)
            self.assertEqual(menu.parent_id, tech_root, f"{xmlid} ليس تحت تطبيق المكتب الفني")

    def test_execution_menus_stay_under_construction_app(self):
        execution_root = self.env.ref("rawasi_construction.menu_rawasi_root")

        for xmlid in (
            "rawasi_construction.menu_rawasi_projects",
            "rawasi_construction.menu_rawasi_wbs",
            "rawasi_construction.menu_rawasi_procurement",
            "rawasi_construction.menu_rawasi_field",
            "rawasi_construction.menu_rawasi_contracts",
            "rawasi_construction.menu_rawasi_config",
        ):
            menu = self.env.ref(xmlid)
            self.assertEqual(menu.parent_id, execution_root, f"{xmlid} ليس تحت تطبيق التنفيذ")

    def test_pricing_settings_are_not_execution_settings(self):
        tech_config = self.env.ref("rawasi_construction.menu_rawasi_technical_office_config")
        execution_config = self.env.ref("rawasi_construction.menu_rawasi_config")

        self.assertEqual(
            self.env.ref("rawasi_construction.menu_rawasi_units").parent_id,
            tech_config,
        )
        self.assertEqual(
            self.env.ref("rawasi_construction.menu_rawasi_sbc").parent_id,
            tech_config,
        )
        self.assertEqual(
            self.env.ref("rawasi_construction.menu_rawasi_wbs_phase").parent_id,
            execution_config,
        )

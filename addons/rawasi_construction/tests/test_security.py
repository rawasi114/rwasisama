# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRawasiSecurity(TransactionCase):
    """Phase 0: verify the 7 persona groups install and the CEO is a superset."""

    PERSONA_XMLIDS = [
        "rawasi_construction.group_ceo",
        "rawasi_construction.group_projects_director",
        "rawasi_construction.group_tech_office_manager",
        "rawasi_construction.group_planning_engineer",
        "rawasi_construction.group_site_engineer",
        "rawasi_construction.group_accountant",
        "rawasi_construction.group_external_consultant",
    ]

    def test_all_persona_groups_exist(self):
        for xmlid in self.PERSONA_XMLIDS:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(group, f"المجموعة مفقودة: {xmlid}")

    def test_groups_in_rawasi_privilege(self):
        privilege = self.env.ref("rawasi_construction.privilege_rawasi_role")
        category = self.env.ref("rawasi_construction.module_category_rawasi")
        self.assertEqual(privilege.category_id, category)
        for xmlid in self.PERSONA_XMLIDS:
            group = self.env.ref(xmlid)
            self.assertEqual(
                group.privilege_id, privilege,
                f"{xmlid} ليست ضمن صلاحية رواسي سما",
            )

    def test_ceo_is_superset(self):
        ceo = self.env.ref("rawasi_construction.group_ceo")
        for xmlid in self.PERSONA_XMLIDS:
            if xmlid.endswith("group_ceo"):
                continue
            group = self.env.ref(xmlid)
            self.assertIn(
                group, ceo.implied_ids,
                f"المدير العام لا يرث {xmlid}",
            )

    def test_personas_are_internal_users(self):
        internal = self.env.ref("base.group_user")
        for xmlid in self.PERSONA_XMLIDS:
            group = self.env.ref(xmlid)
            self.assertIn(
                internal, group.all_implied_ids,
                f"{xmlid} ليست مستخدماً داخلياً",
            )

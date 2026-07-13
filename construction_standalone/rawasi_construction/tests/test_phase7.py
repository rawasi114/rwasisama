# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPhase7Dashboards(TransactionCase):
    ACTIONS = [
        "rawasi_construction.action_dash_competition",
        "rawasi_construction.action_dash_ipc",
        "rawasi_construction.action_dash_budget",
        "rawasi_construction.action_dash_ncr",
        "rawasi_construction.action_dash_rfi",
        "rawasi_construction.action_dash_bg",
    ]

    def test_dashboard_actions_exist(self):
        for xmlid in self.ACTIONS:
            action = self.env.ref(xmlid)
            self.assertTrue(action)
            self.assertIn("graph", action.view_mode)

    def test_graph_views_load(self):
        # get_views يصرّف بنية العروض ويتأكد من صحتها
        self.env["rawasi.competition"].get_views(
            [(self.env.ref("rawasi_construction.view_competition_graph").id, "graph")]
        )
        self.env["rawasi.payment.certificate"].get_views(
            [(self.env.ref("rawasi_construction.view_pc_pivot").id, "pivot")]
        )
        self.env["rawasi.bank.guarantee"].get_views(
            [(self.env.ref("rawasi_construction.view_bg_graph").id, "graph")]
        )

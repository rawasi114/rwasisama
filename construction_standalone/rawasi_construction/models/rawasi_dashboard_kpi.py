# -*- coding: utf-8 -*-
"""لوحة تحكم حيّة — KPI Cards حسب دور المستخدم.

يكشف Method `get_dashboard_data()` بطاقات قابلة للضغط لكل دور:
  • CEO: NCR حرج، VO معلَّق، IPC بانتظار
  • Projects Director: مشاريع، NCR، VO، MR
  • Site Engineer: DSR اليوم، MAS بانتظار، NCR، MR مرفوض
  • Accountant: IPC، ضمانات قريبة الانتهاء، VO للفوترة
  • Tech Office Manager: اعتماد فني وطلبات مرتبطة بالتنفيذ
  • Planning Engineer: مشاريع نشطة
  • External Consultant: MAS/RFI/IPC بانتظاره

كل بطاقة تفتح action رسمي مع domain filter جاهز.
"""
from odoo import api, fields, models


class RawasiDashboardKpi(models.AbstractModel):
    _name = "rawasi.dashboard.kpi"
    _description = "حسابات لوحة التحكم الحيّة"

    @api.model
    def get_dashboard_data(self):
        """يرجع dict شامل: user info + قائمة بطاقات حسب أدوار المستخدم."""
        user = self.env.user
        groups = {
            "ceo": user.has_group("rawasi_construction.group_ceo"),
            "director": user.has_group("rawasi_construction.group_projects_director"),
            "tech": user.has_group("rawasi_construction.group_tech_office_manager"),
            "planning": user.has_group("rawasi_construction.group_planning_engineer"),
            "site": user.has_group("rawasi_construction.group_site_engineer"),
            "accountant": user.has_group("rawasi_construction.group_accountant"),
            "consultant": user.has_group("rawasi_construction.group_external_consultant"),
        }

        cards = []
        seen = set()  # نمنع تكرار البطاقة لو الدور تابع لدور أعلى

        def add(key, **kw):
            if key in seen:
                return
            seen.add(key)
            cards.append(kw | {"key": key})

        # ── بطاقات تنفيذية (CEO + Director) ─────────────────────
        if groups["ceo"] or groups["director"]:
            vo_pending = self.env["rawasi.variation.order"].search_count(
                [("state", "=", "submitted")]
            )
            add("vo_pending", title="VO بانتظار الاعتماد", value=vo_pending,
                icon="fa-file-signature", color="warning",
                action="rawasi_construction.action_variation_order",
                domain=[("state", "=", "submitted")])

            ipc_pending = self.env["rawasi.payment.certificate"].search_count(
                [("state", "in", ("submitted",))]
            )
            add("ipc_pending", title="IPC بانتظار الاعتماد", value=ipc_pending,
                icon="fa-file-invoice-dollar", color="warning",
                action="rawasi_construction.action_payment_certificate",
                domain=[("state", "=", "submitted")])

            ncr_critical = self.env["rawasi.ncr"].search_count(
                [("severity", "=", "critical"),
                 ("state", "in", ("open", "in_progress"))]
            )
            add("ncr_critical", title="NCR حرج مفتوح", value=ncr_critical,
                icon="fa-exclamation-triangle",
                color="danger" if ncr_critical else "success",
                action="rawasi_construction.action_ncr",
                domain=[("severity", "=", "critical"),
                        ("state", "in", ("open", "in_progress"))])

        # ── ضمانات بنكية (CEO + Accountant) ─────────────────────
        if groups["ceo"] or groups["accountant"]:
            bg_soon = self.env["rawasi.bank.guarantee"].search_count(
                [("expiry_state", "=", "soon"), ("state", "=", "active")]
            )
            add("bg_soon", title="ضمانات قريبة الانتهاء", value=bg_soon,
                icon="fa-shield-alt",
                color="danger" if bg_soon else "success",
                action="rawasi_construction.action_bank_guarantee",
                domain=[("expiry_state", "=", "soon"), ("state", "=", "active")])

        # ── المشتريات (Director + Site + Accountant) ────────────
        if groups["ceo"] or groups["director"] or groups["tech"] or groups["accountant"]:
            mr_pending = self.env["rawasi.material.request"].search_count(
                [("state", "=", "submitted")]
            )
            add("mr_pending", title="MR بانتظار الاعتماد", value=mr_pending,
                icon="fa-shopping-cart",
                color="warning" if mr_pending else "info",
                action="rawasi_construction.action_material_request",
                domain=[("state", "=", "submitted")])

            mr_over = self.env["rawasi.material.request"].search_count(
                [("has_over_budget", "=", True),
                 ("state", "in", ("draft", "submitted", "approved")),
                 ("override_budget", "=", False)]
            )
            add("mr_over", title="MR متجاوز الميزانية", value=mr_over,
                icon="fa-money-bill-wave",
                color="danger" if mr_over else "success",
                action="rawasi_construction.action_material_request",
                domain=[("has_over_budget", "=", True),
                        ("override_budget", "=", False)])

        # ── مهندس الموقع ─────────────────────────────────────────
        if groups["ceo"] or groups["site"]:
            today = fields.Date.context_today(self)
            dsr_today = self.env["rawasi.daily.report"].search_count(
                [("report_date", "=", today)]
            )
            add("dsr_today", title="DSR لليوم", value=dsr_today,
                icon="fa-clipboard-check",
                color="success" if dsr_today else "warning",
                action="rawasi_construction.action_daily_report",
                domain=[("report_date", "=", today.strftime("%Y-%m-%d"))])

            mas_waiting = self.env["rawasi.material.approval"].search_count(
                [("state", "=", "submitted")]
            )
            add("mas_waiting", title="MAS بانتظار الاستشاري",
                value=mas_waiting,
                icon="fa-cubes", color="info",
                action="rawasi_construction.action_material_approval",
                domain=[("state", "=", "submitted")])

            ncr_open_mine = self.env["rawasi.ncr"].search_count(
                [("state", "in", ("open", "in_progress")),
                 ("responsible_id", "=", user.id)]
            )
            add("ncr_open_mine", title="NCR مسؤوليّتي",
                value=ncr_open_mine,
                icon="fa-tasks",
                color="warning" if ncr_open_mine else "success",
                action="rawasi_construction.action_ncr",
                context={"search_default_f_my_responsibility": 1,
                         "search_default_f_open": 1})

            rfi_pending = self.env["rawasi.rfi"].search_count(
                [("state", "in", ("draft", "submitted"))]
            )
            add("rfi_pending", title="RFI بانتظار رد", value=rfi_pending,
                icon="fa-question-circle", color="info",
                action="rawasi_construction.action_rfi",
                domain=[("state", "in", ("draft", "submitted"))])

        # ── الاستشاري الخارجي ────────────────────────────────────
        if groups["consultant"]:
            mas_for_consultant = self.env["rawasi.material.approval"].search_count(
                [("state", "=", "submitted")]
            )
            add("mas_consultant", title="MAS بانتظار مراجعتي",
                value=mas_for_consultant,
                icon="fa-user-check",
                color="warning" if mas_for_consultant else "success",
                action="rawasi_construction.action_material_approval",
                domain=[("state", "=", "submitted")])

            rfi_for_consultant = self.env["rawasi.rfi"].search_count(
                [("state", "=", "submitted")]
            )
            add("rfi_consultant", title="RFI بانتظار ردّي",
                value=rfi_for_consultant,
                icon="fa-question",
                color="warning" if rfi_for_consultant else "success",
                action="rawasi_construction.action_rfi",
                domain=[("state", "=", "submitted")])

        return {
            "user_name": user.name,
            "today": fields.Date.context_today(self).isoformat(),
            "cards": cards,
        }

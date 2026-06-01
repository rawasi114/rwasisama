# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RawasiDailyReport(models.Model):
    _name = "rawasi.daily.report"
    _description = "التقرير اليومي للموقع (Daily Site Report)"
    _inherit = [
        "mail.thread", "mail.activity.mixin",
        "rawasi.workflow.mixin", "rawasi.printable.mixin",
    ]
    _order = "report_date desc, id desc"

    name = fields.Char(
        string="الرقم", default="/", readonly=True, copy=False
    )
    project_id = fields.Many2one(
        "project.project", string="المشروع", required=True, tracking=True
    )
    report_date = fields.Date(
        string="التاريخ", default=fields.Date.context_today, required=True, tracking=True
    )
    prepared_by_id = fields.Many2one(
        "res.users", string="أعدّه", default=lambda self: self.env.user
    )
    weather = fields.Selection(
        [
            ("clear", "صحو"),
            ("cloudy", "غائم"),
            ("rain", "ممطر"),
            ("hot", "حار"),
            ("sandstorm", "عاصفة رملية"),
        ],
        string="الطقس",
        default="clear",
    )
    temperature = fields.Integer(string="درجة الحرارة °م")
    work_done = fields.Text(string="الأعمال المنفّذة")
    delays = fields.Text(string="المعوقات/التأخيرات")
    equipment = fields.Text(string="المعدات في الموقع")
    visitors = fields.Char(string="الزوار")
    labor_ids = fields.One2many(
        "rawasi.daily.report.labor", "report_id", string="العمالة"
    )
    progress_line_ids = fields.One2many(
        "rawasi.dsr.progress.line", "report_id", string="إنجاز البنود",
    )
    consumption_line_ids = fields.One2many(
        "rawasi.dsr.consumption.line", "report_id", string="استهلاك المواد",
    )
    total_workers = fields.Integer(
        string="إجمالي العمالة", compute="_compute_total_workers", store=True
    )
    stock_picking_id = fields.Many2one(
        "stock.picking", string="إذن صرف الاستهلاك", readonly=True, copy=False,
        help="إذن داخلي يُنشأ تلقائياً عند تأكيد DSR لنقل المواد من العُهد إلى موقع التنفيذ.",
    )
    state = fields.Selection(
        [("draft", "مسودة"), ("confirmed", "معتمد")],
        string="الحالة",
        default="draft",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "rawasi_dsr_attachment_rel",
        "report_id",
        "attachment_id",
        string="الصور/المرفقات",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "rawasi.daily.report"
                ) or "/"
        return super().create(vals_list)

    @api.depends("labor_ids.worker_count")
    def _compute_total_workers(self):
        for rep in self:
            rep.total_workers = sum(rep.labor_ids.mapped("worker_count"))

    def _report_xmlid(self):
        return "rawasi_construction.action_report_dsr"

    def action_confirm(self):
        for rep in self:
            rep._validate_progress_lines()
            rep._create_consumption_picking()
        self.write({"state": "confirmed"})

    def _validate_progress_lines(self):
        """يمنع تجاوز الكمية المتعاقد عليها للبند."""
        self.ensure_one()
        for line in self.progress_line_ids:
            if line.qty_today <= 0:
                continue
            item = line.boq_item_id
            other_done = sum(
                ln.qty_today for ln in item.dsr_progress_line_ids
                if ln.id != line.id and ln.report_state == "confirmed"
            )
            if item.quantity and (other_done + line.qty_today) > item.quantity:
                raise UserError(_(
                    "كمية الإنجاز للبند «%(b)s» (%(q).2f) ستتجاوز الكمية "
                    "المتعاقد عليها (%(t).2f). المنجَز سابقاً: %(d).2f."
                ) % {
                    "b": item.name or "", "q": line.qty_today,
                    "t": item.quantity, "d": other_done,
                })

    def _create_consumption_picking(self):
        """يُنشئ إذن نقل داخلي من عُهد المهندسين إلى موقع التنفيذ في المشروع."""
        self.ensure_one()
        lines = self.consumption_line_ids.filtered(lambda l: l.qty > 0)
        if not lines:
            return False
        project = self.project_id
        project._ensure_rawasi_project_location()
        wip = project.rawasi_wip_location_id
        if not wip:
            raise UserError(_("لا يوجد موقع تنفيذ مهيأ للمشروع."))
        Picking = self.env["stock.picking"]
        Move = self.env["stock.move"]
        company_id = project.company_id.id or self.env.company.id
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company_id)], limit=1,
        )
        picking_type = warehouse.int_type_id if warehouse else False
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "internal")], limit=1,
            )
        if not picking_type:
            raise UserError(_("لا يوجد نوع إذن نقل داخلي مهيأ."))
        # نجمّع السطور حسب موقع المصدر (عهدة كل مهندس) لإذن واحد
        # (stock.move يدعم مصادر متعددة في picking واحد طالما الـ destination ثابت)
        picking_vals = {
            "picking_type_id": picking_type.id,
            "location_id": lines[0].custody_id.location_id.id,
            "location_dest_id": wip.id,
            "origin": self.name,
            "partner_id": project.partner_id.id if project.partner_id else False,
            "company_id": project.company_id.id or self.env.company.id,
        }
        picking = Picking.create(picking_vals)
        for ln in lines:
            if not ln.custody_id or not ln.product_id:
                raise UserError(_(
                    "كل سطر استهلاك يحتاج عهدة مصدر ومنتج. السطر: %s"
                ) % (ln.notes or "—"))
            Move.create({
                "product_id": ln.product_id.id,
                "product_uom_qty": ln.qty,
                "product_uom": ln.product_id.uom_id.id,
                "description_picking": ln.product_id.display_name,
                "location_id": ln.custody_id.location_id.id,
                "location_dest_id": wip.id,
                "picking_id": picking.id,
                "company_id": picking.company_id.id,
            })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            for ml in move.move_line_ids:
                ml.quantity = move.product_uom_qty
            if not move.move_line_ids:
                self.env["stock.move.line"].create({
                    "move_id": move.id,
                    "product_id": move.product_id.id,
                    "product_uom_id": move.product_uom.id,
                    "quantity": move.product_uom_qty,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "picking_id": picking.id,
                })
        picking.button_validate()
        self.stock_picking_id = picking.id
        return picking

    def action_open_picking(self):
        self.ensure_one()
        if not self.stock_picking_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": self.stock_picking_id.id,
            "view_mode": "form",
        }

    def action_reset_to_draft(self):
        self._ensure_admin()
        self.write({"state": "draft"})


class RawasiDailyReportLabor(models.Model):
    _name = "rawasi.daily.report.labor"
    _description = "سطر عمالة في التقرير اليومي"

    report_id = fields.Many2one(
        "rawasi.daily.report", required=True, ondelete="cascade"
    )
    trade = fields.Char(string="التخصص", required=True)
    worker_count = fields.Integer(string="العدد", default=0)
    note = fields.Char(string="ملاحظة")


class RawasiDsrProgressLine(models.Model):
    """سطر إنجاز بند جدول الكميات ضمن تقرير يومي.

    يربط الكمية المنفّذة اليومية بالبند المرجعي (BoQ)، ويتغذّى منه
    qty_executed/qty_remaining/qty_executed_pct على البند تلقائياً.
    """

    _name = "rawasi.dsr.progress.line"
    _description = "سطر إنجاز بنود في التقرير اليومي"

    report_id = fields.Many2one(
        "rawasi.daily.report", string="التقرير", required=True,
        ondelete="cascade", index=True,
    )
    project_id = fields.Many2one(
        related="report_id.project_id", store=True, index=True,
    )
    competition_id = fields.Many2one(
        related="project_id.rawasi_competition_id", store=True,
    )
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="البند", required=True,
        ondelete="restrict", index=True,
        domain="[('competition_id','=',competition_id)]",
    )
    name = fields.Text(related="boq_item_id.name", string="الوصف")
    unit_id = fields.Many2one(related="boq_item_id.unit_id", string="الوحدة")
    qty_contract = fields.Float(related="boq_item_id.quantity", string="الكمية التعاقدية")
    qty_today = fields.Float(string="منفَّذ اليوم", required=True, default=0.0)
    qty_remaining_after = fields.Float(
        string="المتبقي بعد اليوم", compute="_compute_qty_remaining_after",
    )
    notes = fields.Char(string="ملاحظات")
    report_state = fields.Selection(
        related="report_id.state", store=True, index=True,
    )

    @api.depends("qty_today", "boq_item_id.qty_executed", "report_state")
    def _compute_qty_remaining_after(self):
        for ln in self:
            item = ln.boq_item_id
            if not item:
                ln.qty_remaining_after = 0.0
                continue
            already = item.qty_executed if ln.report_state == "confirmed" else (
                item.qty_executed + ln.qty_today
            )
            ln.qty_remaining_after = max((item.quantity or 0.0) - already, 0.0)


class RawasiDsrConsumptionLine(models.Model):
    """سطر استهلاك مادة من عهدة مهندس في يوم معيّن.

    عند تأكيد DSR يُنشأ stock.move من موقع العهدة إلى موقع التنفيذ (WIP)،
    فيُسحب من الجرد الفعلي للمهندس ويُحتسب ضمن استهلاك المشروع.
    """

    _name = "rawasi.dsr.consumption.line"
    _description = "سطر استهلاك مواد في التقرير اليومي"

    report_id = fields.Many2one(
        "rawasi.daily.report", string="التقرير", required=True,
        ondelete="cascade", index=True,
    )
    project_id = fields.Many2one(
        related="report_id.project_id", store=True, index=True,
    )
    competition_id = fields.Many2one(
        related="project_id.rawasi_competition_id", store=True,
    )
    custody_id = fields.Many2one(
        "rawasi.engineer.custody", string="عهدة المصدر", required=True,
        ondelete="restrict",
        domain="[('project_id','=',project_id),('active','=',True)]",
    )
    product_id = fields.Many2one(
        "product.product", string="المنتج", required=True,
        domain="[('is_construction','=',True)]",
    )
    qty = fields.Float(string="الكمية", required=True, default=0.0)
    uom_id = fields.Many2one(
        related="product_id.uom_id", string="الوحدة", readonly=True,
    )
    boq_item_id = fields.Many2one(
        "rawasi.boq.item", string="بند مرجعي (اختياري)",
        domain="[('competition_id','=',competition_id)]",
        help="رابط اختياري للبند الذي يخدمه هذا الاستهلاك (للتحليل اللاحق فقط).",
    )
    notes = fields.Char(string="ملاحظات")
    available_qty = fields.Float(
        string="المتاح في العهدة", compute="_compute_available_qty",
    )

    @api.depends("custody_id", "product_id")
    def _compute_available_qty(self):
        Quant = self.env["stock.quant"]
        for ln in self:
            if not ln.custody_id or not ln.product_id:
                ln.available_qty = 0.0
                continue
            quants = Quant.search([
                ("location_id", "=", ln.custody_id.location_id.id),
                ("product_id", "=", ln.product_id.id),
            ])
            ln.available_qty = sum(quants.mapped("quantity"))

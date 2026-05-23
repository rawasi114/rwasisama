# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleMrpProductivityReport(models.TransientModel):
    _name = 'simple.mrp.productivity.report'
    _description = "تقرير الإنتاجية"

    report_type = fields.Selection([
        ('daily', "يومي"),
        ('weekly', "أسبوعي"),
    ], string="نوع التقرير", default='daily')
    date_from = fields.Date(
        string="من", default=fields.Date.context_today)
    date_to = fields.Date(
        string="إلى", default=fields.Date.context_today)
    line_ids = fields.One2many(
        'simple.mrp.productivity.report.line', 'report_id', string="النتائج")

    def get_report_data(self):
        """يجمّع أوامر التصنيع المنجزة حسب المنتج خلال الفترة."""
        self.ensure_one()
        self.line_ids.unlink()
        domain = [
            ('state', 'in', ('done', 'delivered', 'closed')),
            ('date_planned', '>=', self.date_from),
            ('date_planned', '<=', self.date_to),
        ]
        orders = self.env['simple.mrp.order'].search(domain)
        grouped = {}
        for mo in orders:
            key = mo.product_id
            data = grouped.setdefault(key, {'count': 0, 'qty': 0.0})
            data['count'] += 1
            data['qty'] += mo.product_qty
        lines = []
        for product, data in grouped.items():
            lines.append((0, 0, {
                'product_id': product.id,
                'order_count': data['count'],
                'total_qty': data['qty'],
            }))
        self.line_ids = lines
        return True

    def action_print(self):
        self.get_report_data()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'simple.mrp.productivity.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class SimpleMrpProductivityReportLine(models.TransientModel):
    _name = 'simple.mrp.productivity.report.line'
    _description = "بند تقرير الإنتاجية"
    _order = 'id'

    report_id = fields.Many2one(
        'simple.mrp.productivity.report', string="التقرير", ondelete='cascade')
    product_id = fields.Many2one('product.product', string="المنتج")
    order_count = fields.Integer(string="عدد الأوامر")
    total_qty = fields.Float(string="إجمالي الكمية")

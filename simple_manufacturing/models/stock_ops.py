# -*- coding: utf-8 -*-
"""دوال مساعدة للتعامل مع مخزون أودو القياسي (stock.quant) كمصدر وحيد."""


def workshop_stock_location(env):
    """يرجع موقع المخزون الداخلي الافتراضي لشركة المستخدم الحالية."""
    warehouse = env['stock.warehouse'].sudo().search(
        [('company_id', '=', env.company.id)], limit=1)
    if warehouse and warehouse.lot_stock_id:
        return warehouse.lot_stock_id
    return env['stock.location'].sudo().search(
        [('usage', '=', 'internal'), ('company_id', 'in', [env.company.id, False])],
        limit=1)


def available_qty(env, product, location=None):
    """الكمية المتاحة بالمخزون لمنتج في موقع (الموقع الداخلي افتراضياً)."""
    if not product:
        return 0.0
    location = location or workshop_stock_location(env)
    if not location:
        return 0.0
    return product.with_context(location=location.id).qty_available


def change_stock(env, product, qty, location=None):
    """يعدّل الكمية المتاحة لمنتج في المخزون القياسي (موجب=إضافة، سالب=خصم)."""
    if not product or not qty:
        return
    location = location or workshop_stock_location(env)
    if not location:
        return
    env['stock.quant'].sudo()._update_available_quantity(product, location, qty)

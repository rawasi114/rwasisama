# -*- coding: utf-8 -*-
"""تعديل ترقيم القيود المحاسبية (الفواتير والدفعات) ليبدأ من 10001.

في Odoo 19، أول رقم في تسلسل الدفتر يُحدَّد عبر
``sequence.mixin._get_next_sequence_format`` الذي يصفّر ``seq=0`` ثم
``_set_next_sequence`` يزيد ١ → فيصبح أول مستند = ``INV/YYYY/00001``.

نتجاوز ``_get_next_sequence_format`` فقط على ``account.move`` حين يكون
الدفتر بلا أي حركة سابقة (أول مستند)، ونرفع نقطة البدء إلى ١٠٠٠٠ →
فأول مستند يصبح ``INV/YYYY/10001``.

التأثير شامل على:
- فواتير العملاء (out_invoice) + إشعارات دائنة (out_refund)
- فواتير الموردين (in_invoice) + إشعارات مدينة (in_refund)
- دفعات البنك والصندوق (account.payment تستخدم account.move داخلياً)
- القيود اليدوية على دفاتر القيود
"""

from odoo import models


RAWASI_STARTING_OFFSET = 10000  # أول مستند بعد +١ سيكون 10001


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_next_sequence_format(self):
        """يرفع ``seq`` إلى ١٠٠٠٠ بدل ٠ حين يكون أول مستند في الدفتر."""
        format_string, format_values = super()._get_next_sequence_format()
        # `_get_last_sequence()` بلا relaxed يرجع False = أول مستند فعلي
        if not self._get_last_sequence() and format_values.get("seq") == 0:
            format_values["seq"] = RAWASI_STARTING_OFFSET
        return format_string, format_values

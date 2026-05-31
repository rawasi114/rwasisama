# -*- coding: utf-8 -*-
from . import models
from . import wizards
from .post_init import load_chart_of_accounts


def _rawasi_post_init_hook(env):
    """يُنفَّذ عند تثبيت الموديول لأول مرة فقط:
    1) تحميل ``generic_coa`` (للحصول على الدفاتر + الضرائب)
    2) إنشاء شجرة حسابات رواسي الـ272 حساباً
    3) ضبط تسلسلات sale.order / purchase.order على 10001
    """
    load_chart_of_accounts(env)

# -*- coding: utf-8 -*-
from . import models
from . import wizards


def _rawasi_post_init_hook(env):
    """يحمّل شجرة حسابات رواسي (272 حساب) بعد تثبيت الموديول."""
    from . import post_init
    post_init.load_chart_of_accounts(env)

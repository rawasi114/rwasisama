# -*- coding: utf-8 -*-
"""Grant admin user the catalog admin group on existing installs.

post_init_hook only fires on fresh installs; databases that installed
an earlier version of this module won't get the admin-group assignment
that bootstraps menu visibility. This migration runs once when the user
upgrades to >= 19.0.2.0.3 and adds the admin user to the admin group.
Idempotent — `(4, id)` is a no-op if the user is already a member.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    admin_group = env.ref(
        "rawasi_item_catalog.group_item_catalog_admin",
        raise_if_not_found=False,
    )
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if admin_group and admin_user:
        admin_group.write({"user_ids": [(4, admin_user.id)]})
        _logger.info(
            "rawasi_item_catalog: granted admin user the catalog admin group"
        )
    else:
        _logger.warning(
            "rawasi_item_catalog: could not auto-grant admin group "
            "(group=%s, user=%s)", admin_group, admin_user,
        )

# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rawasi_mol_establishment_id = fields.Char(
        related="company_id.rawasi_mol_establishment_id", readonly=False
    )
    rawasi_wps_bank_id = fields.Many2one(
        related="company_id.rawasi_wps_bank_id", readonly=False
    )
    rawasi_wps_format = fields.Selection(
        related="company_id.rawasi_wps_format", readonly=False
    )
    rawasi_eos_wage_base_policy = fields.Selection(
        related="company_id.rawasi_eos_wage_base_policy", readonly=False
    )
    rawasi_eos_provision_account_id = fields.Many2one(
        related="company_id.rawasi_eos_provision_account_id", readonly=False
    )
    rawasi_eos_payable_account_id = fields.Many2one(
        related="company_id.rawasi_eos_payable_account_id", readonly=False
    )
    rawasi_eos_expense_account_id = fields.Many2one(
        related="company_id.rawasi_eos_expense_account_id", readonly=False
    )
    rawasi_eos_journal_id = fields.Many2one(
        related="company_id.rawasi_eos_journal_id", readonly=False
    )

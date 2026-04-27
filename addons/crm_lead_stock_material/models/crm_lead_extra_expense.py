# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import _, fields, models


class CrmLeadExtraExpense(models.Model):
    _name = "crm.lead.extra.expense"
    _description = "CRM Lead Extra Expense"
    _order = "id"

    lead_id = fields.Many2one(
        "crm.lead",
        string=_("Сделка"),
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string=_("Статья расхода"), required=True)
    amount = fields.Monetary(
        string=_("Сумма"),
        required=True,
        default=0.0,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="lead_id.company_currency",
        string=_("Валюта"),
        store=True,
        readonly=True,
    )
    note = fields.Char(string=_("Примечание"))

# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    crm_lead_id = fields.Many2one(
        "crm.lead",
        string=_("CRM Lead"),
        copy=False,
        index=True,
        ondelete="set null",
    )

# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import _, api, fields, models

from .material_qty_formula import eval_material_qty_formula


class CrmLeadMaterialLine(models.Model):
    _name = "crm.lead.material.line"
    _description = "CRM Lead Material Line"
    _order = "id"

    def _crm_invalidate_calendar_for_leads(self):
        leads = self.mapped("lead_id")
        if leads:
            self.env["calendar.event"]._crm_invalidate_lead_events_display(leads.ids)

    sequence = fields.Integer(default=10)
    lead_id = fields.Many2one(
        "crm.lead",
        string=_("Opportunity"),
        required=True,
        ondelete="cascade",
        index=True,
    )
    kit_template_line_id = fields.Many2one(
        "crm.material.kit.line",
        string=_("Kit line"),
        copy=False,
        ondelete="set null",
        help=_(
            "Set when this row was generated from a material kit. "
            "Empty means a manual line."
        ),
    )
    product_id = fields.Many2one(
        "product.product",
        string=_("Product"),
        required=True,
        domain="[('type', 'in', ('consu', 'product'))]",
    )
    name = fields.Char(string=_("Description"))
    product_uom_id = fields.Many2one(
        "uom.uom",
        string=_("Unit of Measure"),
        required=True,
    )
    product_uom_qty = fields.Float(
        string=_("Quantity"),
        default=1.0,
        digits="Product Unit of Measure",
    )
    qty_formula = fields.Char(
        string=_("Quantity formula"),
        help=_(
            "Optional. x = base quantity on the lead. "
            "If empty or invalid, kit/base quantity is used."
        ),
    )
    formula_base_product_id = fields.Many2one(
        "product.product",
        string=_("Main product (formula)"),
        domain="[('type', 'in', ('consu', 'product'))]",
        help=_("Optional; copied from the kit line."),
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string=_("Warehouse"),
        help=_("If set, on-hand quantity is computed for this warehouse only."),
    )
    qty_available = fields.Float(
        string=_("On Hand"),
        compute="_compute_qty_available",
        digits="Product Unit of Measure",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="lead_id.company_id.currency_id",
        string="Валюта",
        readonly=True,
    )
    sale_price_unit = fields.Float(
        string="Цена продажи",
        compute="_compute_pricing",
        digits="Product Price",
    )
    cost_price_unit = fields.Float(
        string="Цена себестоимости",
        compute="_compute_pricing",
        digits="Product Price",
    )
    sale_subtotal = fields.Monetary(
        string="Сумма продажи",
        compute="_compute_pricing",
        currency_field="currency_id",
    )
    cost_subtotal = fields.Monetary(
        string="Сумма себестоимости",
        compute="_compute_pricing",
        currency_field="currency_id",
    )
    move_id = fields.Many2one(
        "stock.move",
        string=_("Stock move"),
        readonly=True,
        copy=False,
        ondelete="set null",
        groups="stock.group_stock_user",
    )

    @api.depends("product_id", "warehouse_id", "lead_id.company_id")
    def _compute_qty_available(self):
        Location = self.env["stock.location"].sudo()
        Quant = self.env["stock.quant"].sudo()
        for line in self:
            line.qty_available = 0.0
            if not line.product_id or not line.lead_id:
                continue
            company = line.lead_id.company_id
            if line.warehouse_id:
                loc_ids = Location.search(
                    [
                        ("id", "child_of", line.warehouse_id.lot_stock_id.id),
                        ("usage", "=", "internal"),
                    ]
                ).ids
            else:
                loc_ids = Location.search(
                    [
                        ("usage", "=", "internal"),
                        "|",
                        ("company_id", "=", company.id),
                        ("company_id", "=", False),
                    ]
                ).ids
            if not loc_ids:
                continue
            quants = Quant.search(
                [
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "in", loc_ids),
                    ("company_id", "=", company.id),
                ]
            )
            line.qty_available = sum(q.quantity - q.reserved_quantity for q in quants)

    @api.depends("product_id", "product_uom_qty")
    def _compute_pricing(self):
        for line in self:
            if not line.product_id:
                line.sale_price_unit = 0.0
                line.cost_price_unit = 0.0
                line.sale_subtotal = 0.0
                line.cost_subtotal = 0.0
                continue
            sale_price = line.product_id.lst_price or 0.0
            cost_price = line.product_id.standard_price or 0.0
            qty = line.product_uom_qty or 0.0
            line.sale_price_unit = sale_price
            line.cost_price_unit = cost_price
            line.sale_subtotal = sale_price * qty
            line.cost_subtotal = cost_price * qty

    def _fallback_qty_for_formula(self, vals=None):
        self.ensure_one()
        if vals and vals.get("product_uom_qty") is not None:
            return float(vals["product_uom_qty"])
        if self.kit_template_line_id:
            return float(self.kit_template_line_id.product_uom_qty)
        return float(self.product_uom_qty or 0.0)

    def _qty_from_formula(self, x_val, fallback):
        self.ensure_one()
        return eval_material_qty_formula(self.qty_formula, float(x_val), fallback)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.product_uom_id = self.product_id.uom_id
        self.name = self.product_id.display_name
        if self.kit_template_line_id:
            self.kit_template_line_id = False

    @api.onchange("qty_formula", "lead_id")
    def _onchange_qty_formula(self):
        if not self.qty_formula or not self.lead_id:
            return
        fb = self._fallback_qty_for_formula()
        x = float(self.lead_id.material_formula_x)
        self.product_uom_qty = self._qty_from_formula(x, fb)

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            lead_id = vals.get("lead_id")
            if (
                lead_id
                and vals.get("qty_formula")
                and str(vals.get("qty_formula")).strip()
            ):
                lead = self.env["crm.lead"].browse(lead_id)
                kt = vals.get("kit_template_line_id")
                if kt:
                    fb = float(
                        vals.get("product_uom_qty")
                        or self.env["crm.material.kit.line"].browse(kt).product_uom_qty
                    )
                else:
                    fb = float(vals.get("product_uom_qty") or 1.0)
                vals["product_uom_qty"] = eval_material_qty_formula(
                    vals.get("qty_formula"),
                    float(lead.material_formula_x),
                    fb,
                )
            prepared.append(vals)
        lines = super().create(prepared)
        lines._crm_invalidate_calendar_for_leads()
        if not self.env.context.get("skip_material_line_stock_sync"):
            for lead in lines.mapped("lead_id"):
                pick = lead.material_picking_id
                if pick and pick.state == "draft":
                    lead.sudo()._sync_material_picking_moves()
        return lines

    def write(self, vals):
        vals = dict(vals)
        if (
            "qty_formula" in vals
            and str(vals.get("qty_formula") or "").strip()
            and not self.env.context.get("skip_material_formula_recompute")
        ):
            for line in self:
                fb = line._fallback_qty_for_formula(vals)
                new_qty = eval_material_qty_formula(
                    vals.get("qty_formula"),
                    float(line.lead_id.material_formula_x),
                    fb,
                )
                super(CrmLeadMaterialLine, line).write(
                    dict(vals, product_uom_qty=new_qty)
                )
            if self.env.context.get("skip_material_line_stock_sync"):
                self._crm_invalidate_calendar_for_leads()
                return True
            for lead in self.mapped("lead_id"):
                pick = lead.material_picking_id
                if pick and pick.state == "draft":
                    lead.sudo()._sync_material_picking_moves()
            self._crm_invalidate_calendar_for_leads()
            return True
        res = super().write(vals)
        self._crm_invalidate_calendar_for_leads()
        if self.env.context.get("skip_material_line_stock_sync"):
            return res
        for lead in self.mapped("lead_id"):
            pick = lead.material_picking_id
            if pick and pick.state == "draft":
                lead.sudo()._sync_material_picking_moves()
        return res

    def unlink(self):
        leads = self.mapped("lead_id")
        res = super().unlink()
        self.env["calendar.event"]._crm_invalidate_lead_events_display(leads.ids)
        if self.env.context.get("skip_material_line_stock_sync"):
            return res
        for lead in leads:
            if lead.material_picking_id and lead.material_picking_id.state == "draft":
                lead.sudo()._sync_material_picking_moves()
        return res

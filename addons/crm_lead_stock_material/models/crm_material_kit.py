# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import _, api, fields, models


class CrmMaterialKit(models.Model):
    _name = "crm.material.kit"
    _description = "CRM Material Kit"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    is_default = fields.Boolean(
        string=_("Default on new leads"),
        help=_(
            "Only one default kit per company; it is pre-selected on new CRM leads."
        ),
    )
    line_ids = fields.One2many(
        "crm.material.kit.line",
        "kit_id",
        string=_("Lines"),
        copy=True,
    )
    default_material_formula_x = fields.Float(
        string=_("Default base quantity (x)"),
        default=1.0,
        digits="Product Unit of Measure",
        help=_(
            "Pre-filled on the lead when this kit is selected; used as x in line formulas."
        ),
    )
    default_material_base_product_id = fields.Many2one(
        "product.product",
        string=_("Default main product (for x)"),
        domain="[('type', 'in', ('consu', 'product'))]",
        help=_(
            "Pre-filled on the lead when this kit is selected (which product x refers to)."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_default"):
                self._clear_default_for_company(
                    vals.get("company_id", self.env.company.id)
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("is_default"):
            for kit in self:
                self._clear_default_for_company(
                    vals.get("company_id", kit.company_id.id),
                    skip_ids=kit.ids,
                )
        return super().write(vals)

    def _clear_default_for_company(self, company_id, skip_ids=None):
        skip_ids = skip_ids or []
        domain = [
            ("company_id", "=", company_id),
            ("is_default", "=", True),
        ]
        if skip_ids:
            domain.append(("id", "not in", skip_ids))
        self.search(domain).write({"is_default": False})


class CrmMaterialKitLine(models.Model):
    _name = "crm.material.kit.line"
    _description = "CRM Material Kit Line"
    _order = "sequence, id"

    kit_id = fields.Many2one(
        "crm.material.kit",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
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
        required=True,
        digits="Product Unit of Measure",
        help=_("Fallback quantity when the formula is empty or invalid."),
    )
    qty_formula = fields.Char(
        string=_("Quantity formula"),
        help=_(
            "Optional. Variable x is the base quantity on the CRM lead. "
            "Example: x*2+1 or round(x*1.5, 0). "
            "Operators: + - * /. Functions: round, ceil, floor, abs, int, float. "
            "If empty or invalid, the quantity above is used."
        ),
    )
    formula_base_product_id = fields.Many2one(
        "product.product",
        string=_("Main product (formula)"),
        domain="[('type', 'in', ('consu', 'product'))]",
        help=_(
            "Optional reference to the main product the formula relates to "
            "(informational; x is entered on the lead)."
        ),
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.product_uom_id = self.product_id.uom_id
        self.name = self.product_id.display_name

    def name_get(self):
        result = []
        for line in self:
            label = line.name or (
                line.product_id.display_name if line.product_id else ""
            )
            if line.product_uom_qty and line.product_uom_id:
                label = f"{label} × {line.product_uom_qty} {line.product_uom_id.name}"
            result.append((line.id, label or _("Line")))
        return result

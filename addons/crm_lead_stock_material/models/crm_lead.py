# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .material_qty_formula import eval_material_qty_formula


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def _default_material_kit_id(self):
        return self.env["crm.material.kit"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("is_default", "=", True),
                ("active", "=", True),
            ],
            limit=1,
        )

    material_kit_id = fields.Many2one(
        "crm.material.kit",
        string=_("Material kit"),
        domain="[('company_id', 'in', (company_id, False)), ('active', '=', True)]",
        default=_default_material_kit_id,
        help=_(
            "Replaces only rows from this kit. Manual rows and additional kits stay. "
            "Clearing removes rows from this kit only."
        ),
    )
    material_kit_extra_ids = fields.Many2many(
        "crm.material.kit",
        "crm_lead_material_kit_extra_rel",
        "lead_id",
        "kit_id",
        string=_("Additional kits"),
        domain="[('company_id', 'in', (company_id, False)), ('active', '=', True)]",
        help=_(
            "Adds kit lines to the materials list when you add a tag. "
            "Removing a tag does not remove lines (delete rows manually if needed)."
        ),
    )
    material_line_ids = fields.One2many(
        "crm.lead.material.line",
        "lead_id",
        string=_("Materials"),
    )
    material_formula_x = fields.Float(
        string=_("Base quantity (x)"),
        default=1.0,
        digits="Product Unit of Measure",
        help=_("Variable x in material line formulas (shown above the materials list)."),
    )
    material_base_product_id = fields.Many2one(
        "product.product",
        string=_("Main product (for x)"),
        domain="[('type', 'in', ('consu', 'product'))]",
        help=_("Optional: which product the quantity x refers to."),
    )
    material_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string=_("Default warehouse"),
        help=_("Used as stock location when a material line has no warehouse."),
        check_company=True,
    )
    material_picking_id = fields.Many2one(
        "stock.picking",
        string=_("Material delivery"),
        copy=False,
    )
    material_picking_state = fields.Selection(
        related="material_picking_id.state",
        string=_("Delivery state"),
    )

    @api.constrains("material_kit_id", "material_kit_extra_ids")
    def _check_material_kit_extra_overlap(self):
        for lead in self:
            if (
                lead.material_kit_id
                and lead.material_kit_id in lead.material_kit_extra_ids
            ):
                raise UserError(
                    _(
                        "The main material kit cannot be selected as an additional kit."
                    )
                )

    def _lines_from_kit_domain(self, kit):
        """kit is crm.material.kit record"""
        if not kit:
            return self.env["crm.lead.material.line"]
        return self.material_line_ids.filtered(
            lambda l: l.kit_template_line_id
            and l.kit_template_line_id.kit_id == kit
        )

    def _append_kit_lines_from_kit(self, kit):
        """Create material lines from a kit (used for main or extra)."""
        self.ensure_one()
        if not kit:
            return
        LeadLine = self.env["crm.lead.material.line"].with_context(
            skip_material_line_stock_sync=True
        )
        x = float(self.material_formula_x)
        for kl in kit.line_ids.sorted("sequence"):
            fb = float(kl.product_uom_qty)
            qty = eval_material_qty_formula(kl.qty_formula, x, fb)
            LeadLine.create(
                {
                    "lead_id": self.id,
                    "kit_template_line_id": kl.id,
                    "product_id": kl.product_id.id,
                    "product_uom_id": kl.product_uom_id.id,
                    "product_uom_qty": qty,
                    "name": kl.name or kl.product_id.display_name,
                    "sequence": kl.sequence,
                    "qty_formula": kl.qty_formula,
                    "formula_base_product_id": (
                        kl.formula_base_product_id.id
                        if kl.formula_base_product_id
                        else False
                    ),
                }
            )

    def _apply_material_kit(self, old_main_kit_by_lead=None):
        """Replace only rows belonging to the previous main kit; add rows for the new one."""
        old_main_kit_by_lead = old_main_kit_by_lead or {}
        for lead in self:
            old_main_id = old_main_kit_by_lead.get(lead.id)
            old_main = (
                self.env["crm.material.kit"].browse(old_main_id)
                if old_main_id
                else self.env["crm.material.kit"]
            )
            new_main = lead.material_kit_id

            if old_main and new_main and old_main.id == new_main.id:
                continue

            if old_main:
                lead._lines_from_kit_domain(old_main).with_context(
                    skip_material_line_stock_sync=True
                ).unlink()

            if not new_main:
                if (
                    lead.material_picking_id
                    and lead.material_picking_id.state == "draft"
                ):
                    lead.sudo()._sync_material_picking_moves()
                continue

            kit = new_main
            lead.with_context(skip_material_kit_side_effects=True).write(
                {
                    "material_formula_x": kit.default_material_formula_x,
                    "material_base_product_id": (
                        kit.default_material_base_product_id.id
                        if kit.default_material_base_product_id
                        else False
                    ),
                }
            )
            lead._append_kit_lines_from_kit(kit)
            if (
                lead.material_picking_id
                and lead.material_picking_id.state == "draft"
            ):
                lead.sudo()._sync_material_picking_moves()

    def _append_extra_material_kits(self, old_extra_ids_by_lead):
        """Append lines only for newly added extra kits (never remove on tag delete)."""
        for lead in self:
            old_ids = set(old_extra_ids_by_lead.get(lead.id, []))
            new_ids = set(lead.material_kit_extra_ids.ids)
            if lead.material_kit_id:
                new_ids.discard(lead.material_kit_id.id)
            added = new_ids - old_ids
            any_added = False
            for aid in added:
                kit = self.env["crm.material.kit"].browse(aid)
                if not kit:
                    continue
                if lead._lines_from_kit_domain(kit):
                    continue
                lead._append_kit_lines_from_kit(kit)
                any_added = True
            if (
                any_added
                and lead.material_picking_id
                and lead.material_picking_id.state == "draft"
            ):
                lead.sudo()._sync_material_picking_moves()

    def _material_kit_onchange_commands(self):
        """One2many commands for main kit only (extra kit rows stay)."""
        self.ensure_one()
        old_main = self._origin.material_kit_id
        new_main = self.material_kit_id
        if old_main and new_main and old_main.id == new_main.id:
            return []
        cmds = []
        if old_main:
            for line in self.material_line_ids:
                if (
                    line.kit_template_line_id
                    and line.kit_template_line_id.kit_id == old_main
                ):
                    cmds.append((2, line.id))
        if not new_main:
            return cmds
        if self.material_kit_id:
            self.material_formula_x = self.material_kit_id.default_material_formula_x
            self.material_base_product_id = (
                self.material_kit_id.default_material_base_product_id
            )
        x = float(self.material_formula_x)
        for kl in new_main.line_ids.sorted("sequence"):
            cmds.append(
                (
                    0,
                    0,
                    {
                        "kit_template_line_id": kl.id,
                        "product_id": kl.product_id.id,
                        "product_uom_id": kl.product_uom_id.id,
                        "product_uom_qty": eval_material_qty_formula(
                            kl.qty_formula, x, float(kl.product_uom_qty)
                        ),
                        "name": kl.name or kl.product_id.display_name,
                        "sequence": kl.sequence,
                        "qty_formula": kl.qty_formula,
                        "formula_base_product_id": (
                            kl.formula_base_product_id.id
                            if kl.formula_base_product_id
                            else False
                        ),
                    },
                )
            )
        return cmds

    @api.onchange("material_kit_id")
    def _onchange_material_kit_id(self):
        if self.material_kit_id and self.material_kit_id in self.material_kit_extra_ids:
            self.material_kit_extra_ids = self.material_kit_extra_ids - self.material_kit_id
        cmds = self._material_kit_onchange_commands()
        if cmds:
            self.material_line_ids = cmds

    @api.onchange("material_kit_extra_ids")
    def _onchange_material_kit_extra_ids(self):
        if self.material_kit_id and self.material_kit_id in self.material_kit_extra_ids:
            self.material_kit_extra_ids = self.material_kit_extra_ids - self.material_kit_id
        old_ids = set(self._origin.material_kit_extra_ids.ids)
        new_ids = set(self.material_kit_extra_ids.ids)
        if self.material_kit_id:
            new_ids.discard(self.material_kit_id.id)
        added = new_ids - old_ids
        cmds = []
        x = float(self.material_formula_x)
        for aid in added:
            kit = self.env["crm.material.kit"].browse(aid)
            for kl in kit.line_ids.sorted("sequence"):
                cmds.append(
                    (
                        0,
                        0,
                        {
                            "kit_template_line_id": kl.id,
                            "product_id": kl.product_id.id,
                            "product_uom_id": kl.product_uom_id.id,
                            "product_uom_qty": eval_material_qty_formula(
                                kl.qty_formula, x, float(kl.product_uom_qty)
                            ),
                            "name": kl.name or kl.product_id.display_name,
                            "sequence": kl.sequence,
                            "qty_formula": kl.qty_formula,
                            "formula_base_product_id": (
                                kl.formula_base_product_id.id
                                if kl.formula_base_product_id
                                else False
                            ),
                        },
                    )
                )
        if cmds:
            self.material_line_ids = cmds

    def _recompute_material_formula_quantities(self):
        for lead in self:
            x = float(lead.material_formula_x)
            for line in lead.material_line_ids:
                if not str(line.qty_formula or "").strip():
                    continue
                fb = line._fallback_qty_for_formula()
                new_qty = eval_material_qty_formula(line.qty_formula, x, fb)
                line.with_context(
                    skip_material_line_stock_sync=True,
                    skip_material_formula_recompute=True,
                ).write({"product_uom_qty": new_qty})
            if (
                lead.material_picking_id
                and lead.material_picking_id.state == "draft"
            ):
                lead.sudo()._sync_material_picking_moves()

    @api.onchange("material_formula_x")
    def _onchange_material_formula_x(self):
        for line in self.material_line_ids:
            if not str(line.qty_formula or "").strip():
                continue
            fb = line._fallback_qty_for_formula()
            line.product_uom_qty = eval_material_qty_formula(
                line.qty_formula, float(self.material_formula_x), fb
            )

    @api.model_create_multi
    def create(self, vals_list):
        out_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("material_kit_id"):
                vals.pop("material_line_ids", None)
            out_vals.append(vals)
        leads = super().create(out_vals)
        for vals, lead in zip(out_vals, leads):
            lead._apply_material_kit({lead.id: False})
            if "material_line_ids" not in vals:
                lead._append_extra_material_kits({lead.id: []})
        return leads

    def write(self, vals):
        vals = dict(vals)
        # If the form sends material_line_ids, the web client already applied
        # onchange rows (extra kits, etc.); do not append again after super().
        has_o2m_material_lines = "material_line_ids" in vals
        old_main_map = {}
        old_extra_map = {}
        if "material_kit_id" in vals:
            vals.pop("material_line_ids", None)
            for lead in self:
                old_main_map[lead.id] = lead.material_kit_id.id
        if "material_kit_id" in vals or "material_kit_extra_ids" in vals:
            for lead in self:
                old_extra_map[lead.id] = lead.material_kit_extra_ids.ids
        if (
            len(self) == 1
            and vals.get("material_kit_id")
            and "material_kit_extra_ids" not in vals
        ):
            new_main = vals["material_kit_id"]
            lead = self
            if new_main and new_main in lead.material_kit_extra_ids.ids:
                vals["material_kit_extra_ids"] = [
                    (6, 0, [k for k in lead.material_kit_extra_ids.ids if k != new_main])
                ]
        res = super().write(vals)
        if self.env.context.get("skip_material_kit_side_effects"):
            return res
        if "material_kit_extra_ids" in vals and not has_o2m_material_lines:
            self._append_extra_material_kits(old_extra_map)
        if "material_kit_id" in vals:
            self._apply_material_kit(old_main_kit_by_lead=old_main_map)
        elif "material_formula_x" in vals:
            self._recompute_material_formula_quantities()
        return res

    def _get_material_partner(self):
        self.ensure_one()
        if not self.partner_id:
            return self.env["res.partner"]
        return self.partner_id.commercial_partner_id

    def _get_default_material_warehouse(self):
        self.ensure_one()
        if self.material_warehouse_id:
            return self.material_warehouse_id
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )
        if not wh:
            raise UserError(
                _("There is no warehouse for company %s.")
                % (self.company_id.display_name,)
            )
        return wh

    def _get_material_src_location(self, line):
        self.ensure_one()
        if line.warehouse_id:
            return line.warehouse_id.lot_stock_id
        return self._get_default_material_warehouse().lot_stock_id

    def _sync_material_picking_moves(self):
        """Rebuild draft delivery moves from CRM material lines."""
        self.ensure_one()
        if not self.material_picking_id:
            return
        pick = self.material_picking_id.sudo()
        if pick.state != "draft":
            raise UserError(
                _(
                    "The delivery %(name)s is no longer in draft. "
                    "Changing material lines is not allowed. "
                    "Cancel the delivery or adjust stock from Inventory."
                )
                % {"name": pick.name}
            )
        self.material_line_ids.with_context(
            skip_material_line_stock_sync=True
        ).write({"move_id": False})
        pick.move_ids.unlink()
        customer_loc = self.env.ref("stock.stock_location_customers")
        partner = self._get_material_partner()
        partner_id = partner.id if partner else False
        Move = self.env["stock.move"].sudo()
        created = []
        for line in self.material_line_ids:
            src_loc = self._get_material_src_location(line)
            created.append(
                Move.create(
                    {
                        "name": line.name or line.product_id.display_name,
                        "product_id": line.product_id.id,
                        "product_uom": line.product_uom_id.id,
                        "product_uom_qty": line.product_uom_qty,
                        "location_id": src_loc.id,
                        "location_dest_id": customer_loc.id,
                        "picking_id": pick.id,
                        "company_id": self.company_id.id,
                        "partner_id": partner_id,
                    }
                )
            )
        for line, move in zip(self.material_line_ids, created):
            line.sudo().with_context(skip_material_line_stock_sync=True).write(
                {"move_id": move.id}
            )

    def action_create_or_sync_material_picking(self):
        """Create a draft outgoing delivery or refresh moves from material lines."""
        self.ensure_one()
        lead = self.sudo()
        if not lead.material_line_ids:
            raise UserError(_("Add at least one material line."))
        partner = lead._get_material_partner()
        partner_id = partner.id if partner else False

        if lead.material_picking_id:
            lead._sync_material_picking_moves()
            return self._action_open_material_picking()

        wh = lead._get_default_material_warehouse()
        first_line = lead.material_line_ids[0]
        picking_type = (
            first_line.warehouse_id.out_type_id
            if first_line.warehouse_id
            else wh.out_type_id
        )
        first_src = lead._get_material_src_location(first_line)
        customer_loc = lead.env.ref("stock.stock_location_customers")
        pick = lead.env["stock.picking"].sudo().create(
            {
                "picking_type_id": picking_type.id,
                "partner_id": partner_id,
                "location_id": first_src.id,
                "location_dest_id": customer_loc.id,
                "origin": lead.name,
                "company_id": lead.company_id.id,
                "crm_lead_id": lead.id,
            }
        )
        lead.write({"material_picking_id": pick.id})
        lead._sync_material_picking_moves()
        return self._action_open_material_picking()

    def _action_open_material_picking(self):
        self.ensure_one()
        if not self.material_picking_id:
            return True
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": self.material_picking_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_material_picking(self):
        self.ensure_one()
        if not self.material_picking_id:
            raise UserError(_("No material delivery has been created yet."))
        return self._action_open_material_picking()

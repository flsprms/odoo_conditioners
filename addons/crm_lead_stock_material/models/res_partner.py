# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    @api.readonly
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Для выбора участников встречи: сначала контакты внутренних пользователей, потом прочие."""
        if not self.env.context.get("calendar_internal_partners_first"):
            return super().name_search(name, args=args, operator=operator, limit=limit)
        args = args or []
        limit = limit or 100
        if name:
            base_domain = expression.AND([[("display_name", operator, name)], args])
        else:
            base_domain = args

        internal_partner_ids = (
            self.env["res.users"]
            .sudo()
            .search(
                [
                    ("share", "=", False),
                    ("active", "=", True),
                    ("partner_id", "!=", False),
                ]
            )
            .mapped("partner_id")
            .ids
        )

        pri_domain = expression.AND([base_domain, [("id", "in", internal_partner_ids)]])
        rest_domain = expression.AND([base_domain, [("id", "not in", internal_partner_ids)]])

        pri_recs = self.search_fetch(
            pri_domain, ["display_name"], limit=limit, order="complete_name asc, id asc"
        )
        ordered_ids = list(pri_recs.ids)
        if len(ordered_ids) < limit:
            rest_recs = self.search_fetch(
                rest_domain,
                ["display_name"],
                limit=limit - len(ordered_ids),
                order="complete_name asc, id asc",
            )
            ordered_ids.extend(rest_recs.ids)

        records = self.browse(ordered_ids)
        return [(record.id, record.display_name) for record in records]

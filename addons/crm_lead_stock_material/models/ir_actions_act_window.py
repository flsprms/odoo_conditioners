# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from odoo import models
from odoo.tools.safe_eval import safe_eval


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    def read(self, fields=None, load="_classic_read"):
        """Убрать search_default_assigned_to_me («Моя воронка») для выбранных пользователей."""
        result = super().read(fields, load=load)
        user = self.env.user
        if not user or not user._is_internal():
            return result
        if not user.crm_pipeline_show_all_by_default:
            return result
        if fields and "context" not in fields:
            return result
        pipeline = self.env.ref(
            "crm.crm_lead_action_pipeline", raise_if_not_found=False
        )
        if not pipeline:
            return result
        eval_base = dict(self.env.context)
        for values in result:
            if values.get("id") != pipeline.id:
                continue
            ctx_str = values.get("context")
            if not ctx_str:
                continue
            try:
                ctx = safe_eval(ctx_str, eval_base)
            except Exception:
                continue
            if not isinstance(ctx, dict) or "search_default_assigned_to_me" not in ctx:
                continue
            ctx = dict(ctx)
            ctx.pop("search_default_assigned_to_me", None)
            values["context"] = str(ctx)
        return result

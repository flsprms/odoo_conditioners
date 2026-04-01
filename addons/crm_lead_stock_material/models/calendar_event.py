# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from datetime import datetime, time as dt_time, timedelta

import pytz

from odoo import _, api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def _crm_invalidate_lead_events_display(self, lead_ids):
        """Refresh calendar labels when lead material lines change."""
        lead_ids = [lid for lid in lead_ids if lid]
        if not lead_ids:
            return
        events = self.search(
            [
                ("res_model", "=", "crm.lead"),
                ("res_id", "in", lead_ids),
            ]
        )
        if events:
            events.invalidate_recordset(["crm_copper_pipe_card"])

    crm_copper_pipe_card = fields.Char(
        string="Copper pipe (calendar)",
        compute="_compute_crm_copper_pipe_card",
    )

    crm_visit_slot = fields.Selection(
        selection=[
            ("before_lunch", _("Before lunch")),
            ("after_lunch", _("After lunch")),
        ],
        string=_("Visit time"),
        help=_(
            "Sets the start time to morning (09:00) or afternoon (14:00) "
            "in your timezone for the selected day; keeps the current duration."
        ),
        default="before_lunch",
    )

    def _crm_copper_pipe_summary_from_lead(self, lead):
        """Quantities for copper tubes 1/4 and 3/8 from lead material lines."""
        if not lead:
            return ""
        qty_14 = 0.0
        qty_38 = 0.0
        for line in lead.material_line_ids:
            if not line.product_id:
                continue
            name = (line.product_id.name or "").lower()
            if "труба" not in name and "мед" not in name:
                continue
            if "1/4" in name:
                qty_14 += line.product_uom_qty or 0.0
            elif "3/8" in name:
                qty_38 += line.product_uom_qty or 0.0
        parts = []
        if qty_14:
            parts.append(_("1/4: %(q)s m") % {"q": qty_14})
        if qty_38:
            parts.append(_("3/8: %(q)s m") % {"q": qty_38})
        return " | ".join(parts)

    @api.depends("res_model", "res_id")
    def _compute_crm_copper_pipe_card(self):
        lead_model = self.env["crm.lead"]._name
        for event in self:
            if event.res_model != lead_model or not event.res_id:
                event.crm_copper_pipe_card = False
                continue
            lead = self.env["crm.lead"].sudo().browse(event.res_id).exists()
            text = event._crm_copper_pipe_summary_from_lead(lead)
            event.crm_copper_pipe_card = text or False

    @api.onchange("crm_visit_slot")
    def _onchange_crm_visit_slot(self):
        if not self.crm_visit_slot or not self.start:
            return
        user_tz_name = self.env.user.tz or "UTC"
        tz = pytz.timezone(user_tz_name)
        start = fields.Datetime.from_string(self.start)
        if start.tzinfo is None:
            start = pytz.UTC.localize(start)
        start_local = start.astimezone(tz)
        hour = 9 if self.crm_visit_slot == "before_lunch" else 14
        new_local = tz.localize(
            datetime.combine(
                start_local.date(),
                dt_time(hour, 0, 0),
            )
        )
        new_utc = new_local.astimezone(pytz.UTC).replace(tzinfo=None)
        duration_sec = 3600.0
        if self.stop:
            s0 = fields.Datetime.from_string(self.start)
            s1 = fields.Datetime.from_string(self.stop)
            if s0.tzinfo is None:
                s0 = pytz.UTC.localize(s0)
            if s1.tzinfo is None:
                s1 = pytz.UTC.localize(s1)
            duration_sec = max((s1 - s0).total_seconds(), 900.0)
        stop_naive = new_utc + timedelta(seconds=duration_sec)
        self.start = fields.Datetime.to_string(new_utc)
        self.stop = fields.Datetime.to_string(stop_naive)

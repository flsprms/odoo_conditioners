# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

from datetime import datetime, time as dt_time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    # Палитра календаря Odoo: индексы 0–11 (см. colorIndex в web). Держать в sync с
    # SECONDARY_CALENDAR_COLOR_INDEX в static/src/js/calendar_secondary_color_constants.js
    SECONDARY_CALENDAR_COLOR_INDEX = 11

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
        string="Медная труба (календарь)",
        compute="_compute_crm_copper_pipe_card",
    )

    crm_visit_slot = fields.Selection(
        selection=[
            ("before_lunch", "До обеда"),
            ("after_lunch", "После обеда"),
        ],
        string="Время визита",
        help=(
            "Подставляет начало в 09:00 или 14:00 в вашем часовом поясе на выбранный день; "
            "длительность встречи сохраняется."
        ),
    )

    is_secondary = fields.Boolean(
        string="Второстепенная встреча",
        default=False,
        index=True,
        help=(
            "Второстепенные встречи в календаре выделяются одним и тем же цветом "
            "из палитры (12 вариантов) и штриховкой. "
            "Чтобы оставить только их, используйте фильтр «Только второстепенные»."
        ),
    )

    calendar_color_index = fields.Integer(
        string="Цвет в календаре",
        default=1,
        required=True,
        help=(
            "Цвет блока этой встречи в календаре (палитра Odoo, индексы 0–11). "
            "Для второстепенных встреч цвет фиксируется автоматически. "
            "В режиме «Участники» цвет участника может перекрываться настройками календаря."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(v) for v in vals_list]
        for vals in vals_list:
            if vals.get("is_secondary"):
                vals["calendar_color_index"] = self.SECONDARY_CALENDAR_COLOR_INDEX
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("skip_secondary_color_sync"):
            return super().write(vals)
        vals = dict(vals)
        if vals.get("is_secondary"):
            vals["calendar_color_index"] = self.SECONDARY_CALENDAR_COLOR_INDEX
        res = super().write(vals)
        inconsistent = self.filtered(
            lambda e: e.is_secondary
            and e.calendar_color_index != self.SECONDARY_CALENDAR_COLOR_INDEX
        )
        if inconsistent:
            inconsistent.with_context(skip_secondary_color_sync=True).write(
                {"calendar_color_index": self.SECONDARY_CALENDAR_COLOR_INDEX}
            )
        return res

    @api.constrains("calendar_color_index")
    def _check_calendar_color_index(self):
        for event in self:
            c = event.calendar_color_index
            try:
                ci = int(c)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    "Индекс цвета должен быть от 0 до 11."
                ) from exc
            if not (0 <= ci <= 11):
                raise ValidationError(
                    "Индекс цвета должен быть от 0 до 11 (указано: %s)." % c
                )

    @api.onchange("is_secondary")
    def _onchange_is_secondary_calendar_color(self):
        if self.is_secondary:
            self.calendar_color_index = self.SECONDARY_CALENDAR_COLOR_INDEX

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
            parts.append("1/4: %(q)s м" % {"q": qty_14})
        if qty_38:
            parts.append("3/8: %(q)s м" % {"q": qty_38})
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

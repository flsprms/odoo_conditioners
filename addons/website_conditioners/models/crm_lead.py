from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_website_service_type = fields.Selection(
        selection=[
            ("install", "Установка"),
            ("service", "Обслуживание"),
            ("repair", "Ремонт"),
        ],
        string="Тип услуги с сайта",
    )

    def _website_form_lead_name(self, vals):
        """crm.lead.name is required; website form sends contact_name only."""
        if vals.get("name"):
            return vals["name"]
        contact_name = (vals.get("contact_name") or "").strip()
        if not contact_name:
            return False
        service = dict(self._fields["x_website_service_type"].selection).get(
            vals.get("x_website_service_type")
        )
        if service:
            return f"{contact_name} — {service}"
        return contact_name

    @api.model
    def website_form_input_filter(self, request, values):
        values = super().website_form_input_filter(request, values)
        if not values.get("name"):
            lead_name = self._website_form_lead_name(values)
            if lead_name:
                values["name"] = lead_name
        return values

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if not vals.get("name"):
                lead_name = self._website_form_lead_name(vals)
                if lead_name:
                    vals["name"] = lead_name
            prepared.append(vals)
        return super().create(prepared)

from odoo import api, models


class ConditionersWebsiteCleanup(models.TransientModel):
    _name = "conditioners.website.cleanup"
    _description = "Website Conditioners cleanup helpers"

    _CTA_VIEW_KEYS = (
        "website.placeholder_header_call_to_action",
        "website.header_call_to_action",
        "website.header_call_to_action_large",
        "website.header_call_to_action_sidebar",
        "website.header_call_to_action_stretched",
    )

    @api.model
    def run_contact_cleanup(self):
        """Remove Contact us menu items and restore header CTA views."""
        self.env["website.menu"].search([("url", "=", "/contactus")]).unlink()

        contactus_pages = self.env["website.page"].search([("url", "=", "/contactus")])
        if contactus_pages:
            self.env["website.menu"].search(
                [("page_id", "in", contactus_pages.ids)]
            ).unlink()

        # Не отключаем CTA-шаблоны: placeholder нужен для t-call в шапке.
        # Кнопка убирается через xpath в templates/layout.xml.
        cta_views = self.env["ir.ui.view"].with_context(active_test=False).search(
            [("key", "in", self._CTA_VIEW_KEYS)]
        )
        if cta_views:
            cta_views.write({"active": True})

        return True

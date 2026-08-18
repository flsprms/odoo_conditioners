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

        homepage_pages = self.env["website.page"].search([("url", "=", "/")])
        if homepage_pages:
            homepage_pages.write({"name": "Главная"})
        homepage_view = self.env.ref("website.homepage", raise_if_not_found=False)
        if homepage_view:
            homepage_view.write({"name": "Главная"})

        thanks_pages = self.env["website.page"].with_context(active_test=False).search(
            [
                "|",
                ("url", "=", "/contactus-thank-you"),
                ("key", "=", "website.contactus_thanks"),
            ]
        )
        thanks_arch = """<t name="Спасибо" t-name="website.contactus_thanks">
                <t t-call="website.layout">
                    <div id="wrap" class="oe_structure">
                        <t t-call="website_conditioners.s_conditioners_thanks"/>
                    </div>
                </t>
            </t>"""
        for page in thanks_pages:
            page.write({"name": "Спасибо", "arch": thanks_arch})
            if page.view_id:
                page.view_id.write({"name": "Спасибо"})

        text_views = self.env["ir.ui.view"].with_context(active_test=False).search(
            [
                "|",
                ("key", "=", "website.header_text_element"),
                ("key", "like", "website.header_text_element_%"),
            ]
        )
        if text_views:
            text_views.write({"active": False})

        hide_views = self.env["ir.ui.view"].with_context(active_test=False).search(
            [("key", "in", ["website.header_search_box", "portal.user_sign_in"])]
        )
        if hide_views:
            hide_views.write({"active": False})

        self.env["website"].sync_logo_from_companies()

        return True

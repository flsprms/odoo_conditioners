from odoo import models


class Website(models.Model):
    _inherit = "website"

    def _uses_default_logo(self):
        self.ensure_one()
        default_logo = self._default_logo()
        return not self.logo or self.logo == default_logo

    def sync_logo_from_company(self):
        """Copy company logo to website header when website still has the Odoo placeholder."""
        for website in self:
            company = website.company_id
            if not company or company.uses_default_logo or not company.logo:
                continue
            if website._uses_default_logo():
                website.sudo().write({"logo": company.logo})

    def sync_logo_from_companies(self):
        companies = self.env["res.company"].search([("uses_default_logo", "=", False)])
        for company in companies:
            self.search([("company_id", "=", company.id)]).sync_logo_from_company()
        return True


class ResCompany(models.Model):
    _inherit = "res.company"

    def _sync_website_logos(self):
        websites = self.env["website"].search([("company_id", "in", self.ids)])
        websites.sync_logo_from_company()

    def write(self, vals):
        res = super().write(vals)
        if "logo" in vals:
            self._sync_website_logos()
        return res


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        res = super().write(vals)
        if "image_1920" in vals:
            companies = self.env["res.company"].search([("partner_id", "in", self.ids)])
            companies._sync_website_logos()
        return res

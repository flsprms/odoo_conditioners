import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Website(models.Model):
    _inherit = "website"

    contact_phone = fields.Char(
        string="Телефон на сайте",
        help="Как показывать номер посетителям, например +7 (999) 000-00-00.",
    )
    contact_phone_href = fields.Char(
        string="Телефон для ссылки tel:",
        compute="_compute_contact_phone_href",
    )
    contact_max_url = fields.Char(
        string="Ссылка на MAX",
        help="Пусто — кнопки MAX на сайте скрываются.",
    )
    yandex_metrika_id = fields.Char(
        string="Счётчик Яндекс Метрики",
        help="Номер счётчика (только цифры). Пусто — Метрика не подключается. "
        "Счётчик не подгружается сотрудникам, вошедшим в Odoo, "
        "чтобы работа в CRM не попадала в статистику и Вебвизор.",
    )

    @api.depends("contact_phone")
    def _compute_contact_phone_href(self):
        for website in self:
            digits = re.sub(r"\D", "", website.contact_phone or "")
            if len(digits) == 11 and digits.startswith("8"):
                digits = "7" + digits[1:]
            website.contact_phone_href = f"+{digits}" if digits else False

    @api.constrains("yandex_metrika_id")
    def _check_yandex_metrika_id(self):
        for website in self:
            if website.yandex_metrika_id and not website.yandex_metrika_id.isdigit():
                raise ValidationError("Номер счётчика Метрики должен состоять только из цифр.")

    def sync_logo_from_company(self):
        """Copy company logo into the website header (`website.logo`)."""
        for website in self:
            company = website.company_id
            if not company or company.uses_default_logo or not company.logo:
                continue
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

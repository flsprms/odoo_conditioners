from odoo import api, fields, models
from odoo.http import request


class ConditionersFaq(models.Model):
    _name = "conditioners.faq"
    _description = "Website FAQ"
    _order = "sequence, id"

    name = fields.Char(string="Вопрос", required=True)
    answer = fields.Html(string="Ответ", required=True)
    sequence = fields.Integer(default=10)
    is_published = fields.Boolean(string="На сайте", default=True)
    show_on_homepage = fields.Boolean(string="На главной", default=True)
    website_id = fields.Many2one(
        "website",
        string="Сайт",
        ondelete="restrict",
        help="Оставьте пустым, чтобы вопрос отображался на всех сайтах.",
    )

    def _published_domain(self):
        domain = [("is_published", "=", True)]
        website = request.website if request else self.env["website"].get_current_website()
        if website:
            domain += [
                "|",
                ("website_id", "=", False),
                ("website_id", "=", website.id),
            ]
        return domain

    @api.model
    def search_published(self, limit=None, homepage_only=False):
        domain = self._published_domain()
        if homepage_only:
            domain = domain + [("show_on_homepage", "=", True)]
        return self.search(domain, limit=limit, order="sequence, id")

from odoo import api, fields, models
from odoo.http import request


class ConditionersService(models.Model):
    _name = "conditioners.service"
    _description = "Website service"
    _order = "sequence, id"

    name = fields.Char(string="Название", required=True)
    description = fields.Html(string="Описание")
    price_from = fields.Char(string="Цена от")
    icon = fields.Char(
        string="Иконка Font Awesome",
        default="fa-wrench",
        help="Класс иконки, например fa-bolt или fa-wrench.",
    )
    image = fields.Image(string="Фото", max_width=1920, max_height=1920)
    sequence = fields.Integer(default=10)
    is_published = fields.Boolean(string="На сайте", default=True)
    show_on_homepage = fields.Boolean(string="На главной", default=True)
    website_id = fields.Many2one(
        "website",
        string="Сайт",
        ondelete="restrict",
        help="Оставьте пустым, чтобы услуга отображалась на всех сайтах.",
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

from odoo import api, fields, models
from odoo.http import request


class ConditionersReview(models.Model):
    _name = "conditioners.review"
    _description = "Customer review"
    _order = "sequence, id desc"

    name = fields.Char(string="Имя клиента", required=True)
    city = fields.Char(string="Город")
    review_text = fields.Text(string="Текст отзыва")
    image = fields.Image(string="Фото отзыва", max_width=1920, max_height=1920)
    sequence = fields.Integer(default=10)
    is_published = fields.Boolean(string="На сайте", default=True)
    website_id = fields.Many2one(
        "website",
        string="Сайт",
        ondelete="restrict",
        help="Оставьте пустым, чтобы отзыв отображался на всех сайтах.",
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
    def search_published(self, limit=None):
        return self.search(
            self._published_domain(),
            limit=limit,
            order="sequence, id desc",
        )

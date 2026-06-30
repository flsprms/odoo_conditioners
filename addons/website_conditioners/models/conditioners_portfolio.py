from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.http import request


class ConditionersPortfolio(models.Model):
    _name = "conditioners.portfolio"
    _description = "Portfolio photo"
    _order = "sequence, id desc"

    image = fields.Image(
        string="Фото",
        required=True,
        max_width=1920,
        max_height=1920,
    )
    sequence = fields.Integer(default=10)
    is_published = fields.Boolean(string="На сайте", default=True)
    website_id = fields.Many2one(
        "website",
        string="Сайт",
        ondelete="restrict",
        help="Оставьте пустым, чтобы фото отображалось на всех сайтах.",
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


class ConditionersPortfolioUploadWizard(models.TransientModel):
    _name = "conditioners.portfolio.upload.wizard"
    _description = "Bulk portfolio upload"

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "conditioners_portfolio_upload_wizard_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Фотографии",
    )

    def action_upload(self):
        if not self.attachment_ids:
            raise UserError("Выберите хотя бы одно фото.")

        portfolio = self.env["conditioners.portfolio"]
        last = portfolio.search([], order="sequence desc", limit=1)
        sequence = last.sequence if last else 0

        for attachment in self.attachment_ids:
            sequence += 10
            portfolio.create(
                {
                    "image": attachment.datas,
                    "sequence": sequence,
                    "is_published": True,
                }
            )

        return {"type": "ir.actions.act_window_close"}

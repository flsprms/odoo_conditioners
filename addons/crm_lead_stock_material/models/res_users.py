# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    crm_pipeline_show_all_by_default = fields.Boolean(
        string="CRM: показывать все возможности в воронке",
        default=False,
        help=(
            "Если включено, при открытии стандартной «Воронки» не активируется фильтр "
            "«Моя воронка» (по умолчанию только записи, где вы ответственный). "
            "Видны все возможности в пределах прав доступа."
        ),
    )

    def _register_hook(self):
        super()._register_hook()
        # Без обновления модуля (-u) ORM уже знает о поле, а колонки в БД нет.
        # STEP 9 загрузки реестра вызывает _register_hook до первых запросов — создаём колонку здесь.
        cr = self.env.cr
        try:
            cr.execute(
                """
                ALTER TABLE res_users
                ADD COLUMN IF NOT EXISTS crm_pipeline_show_all_by_default boolean DEFAULT false
                """
            )
        except Exception:
            _logger.exception(
                "crm_lead_stock_material: не удалось создать колонку "
                "res_users.crm_pipeline_show_all_by_default"
            )

# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

"""Гарантирует колонку res_users.crm_pipeline_show_all_by_default при любом обновлении модуля.

Сценарий без этого скрипта: контейнер/код обновили, а Apps/`-u` не запускали —
ORM видит поле в Python, в PostgreSQL колонки нет → UndefinedColumn.
"""


def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'res_users'
          AND column_name = 'crm_pipeline_show_all_by_default'
        LIMIT 1
        """
    )
    if cr.fetchone():
        return
    cr.execute(
        """
        ALTER TABLE res_users
        ADD COLUMN crm_pipeline_show_all_by_default boolean DEFAULT false
        """
    )

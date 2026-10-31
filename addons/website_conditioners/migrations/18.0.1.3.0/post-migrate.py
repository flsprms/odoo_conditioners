"""Перенос ранее зашитых в шаблоны контактов и счётчика Метрики в настройки сайта."""

from odoo import SUPERUSER_ID, api

BRAND_NAME = "ВашМонтаж"
PHONE = "+7 (923) 436-37-77"
MAX_URL = "https://max.ru/u/f9LHodD0cOJzh6eAHpIDT9mzvkSp9EmSBi1vHEoy87x8iyjWudjwEMob-ds"
METRIKA_ID = "111660917"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for website in env["website"].search([]):
        vals = {}
        if website.name != BRAND_NAME:
            vals["name"] = BRAND_NAME
        if not website.contact_phone:
            vals["contact_phone"] = PHONE
        if not website.contact_max_url:
            vals["contact_max_url"] = MAX_URL
        if not website.yandex_metrika_id:
            vals["yandex_metrika_id"] = METRIKA_ID
        if vals:
            website.write(vals)

# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

{
    "name": "CRM Lead Stock Materials",
    "summary": "Add material lines (stock products) to CRM leads and opportunities",
    "version": "18.0.1.13.0",
    "sequence": -1000,
    "category": "Sales/CRM",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["crm", "stock", "sales_team", "calendar"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_material_kit_views.xml",
        "views/crm_lead_views.xml",
        "views/stock_picking_views.xml",
        "views/calendar_event_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "crm_lead_stock_material/static/src/xml/calendar_event_templates.xml",
        ],
    },
    "installable": True,
    "application": True,
}

# Copyright 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)

{
    "name": "CRM Lead Stock Materials",
    "summary": "Add material lines (stock products) to CRM leads and opportunities",
    "version": "18.0.1.10.0",
    "sequence": -1000,
    "category": "Sales/CRM",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["crm", "stock", "sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_material_kit_views.xml",
        "views/crm_lead_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": True,
}

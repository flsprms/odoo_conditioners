{
    "name": "Website Conditioners",
    "summary": "Сайт-визитка для установки и обслуживания кондиционеров",
    "version": "18.0.1.0.1",
    "category": "Website",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["website", "website_crm", "crm"],
    "data": [
        "data/website_crm_form.xml",
        "data/website_menu.xml",
        "data/website_pages.xml",
        "views/snippets.xml",
        "templates/layout.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "website_conditioners/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "website_conditioners/static/src/scss/conditioners.scss",
        ],
    },
    "installable": True,
    "application": False,
}

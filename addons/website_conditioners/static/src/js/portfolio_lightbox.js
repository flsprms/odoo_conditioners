/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ConditionersPortfolioLightbox = publicWidget.Widget.extend({
    selector: ".o_conditioners_portfolio_gallery",
    events: {
        "click .o_conditioners_portfolio_link": "_onImageClick",
        "click .o_conditioners_portfolio_prev": "_onPrevClick",
        "click .o_conditioners_portfolio_next": "_onNextClick",
    },

    start() {
        this._links = [...this.el.querySelectorAll(".o_conditioners_portfolio_link")];
        this._currentIndex = 0;
        return this._super(...arguments);
    },

    _onImageClick(ev) {
        ev.preventDefault();
        this._currentIndex = this._links.indexOf(ev.currentTarget);
        this._showCurrent();
    },

    _onPrevClick(ev) {
        ev.preventDefault();
        if (!this._links.length) {
            return;
        }
        this._currentIndex = (this._currentIndex - 1 + this._links.length) % this._links.length;
        this._showCurrent();
    },

    _onNextClick(ev) {
        ev.preventDefault();
        if (!this._links.length) {
            return;
        }
        this._currentIndex = (this._currentIndex + 1) % this._links.length;
        this._showCurrent();
    },

    _showCurrent() {
        const link = this._links[this._currentIndex];
        if (!link) {
            return;
        }
        const modalEl = this.el.querySelector(".modal");
        const imgEl = modalEl?.querySelector(".o_conditioners_portfolio_modal_img");
        if (!modalEl || !imgEl) {
            return;
        }
        imgEl.src = link.getAttribute("href");
        $(modalEl).modal("show");
    },
});

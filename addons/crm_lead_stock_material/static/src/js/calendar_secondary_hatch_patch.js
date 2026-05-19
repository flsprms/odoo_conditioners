/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarModel } from "@web/views/calendar/calendar_model";

import { SECONDARY_CALENDAR_COLOR_INDEX } from "./calendar_secondary_color_constants";

/**
 * Второстепенные встречи — фиксированный цвет из палитры + штриховка (o_event_hatched).
 */
patch(CalendarModel.prototype, {
    normalizeRecord(rawRecord) {
        const record = super.normalizeRecord(...arguments);
        if (rawRecord.is_secondary) {
            record.isHatched = true;
            record.colorIndex = SECONDARY_CALENDAR_COLOR_INDEX;
        }
        return record;
    },
});

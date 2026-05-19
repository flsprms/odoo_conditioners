/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";

import { SECONDARY_CALENDAR_COLOR_INDEX } from "./calendar_secondary_color_constants";

/**
 * Calendar attendee view overwrites colorIndex with the attendee partner id.
 * Restore our explicit calendar_color_index from the server when set;
 * второстепенные — всегда фиксированный цвет палитры.
 */
patch(AttendeeCalendarModel.prototype, {
    async updateAttendeeData(data) {
        await super.updateAttendeeData(...arguments);
        for (const record of Object.values(data.records)) {
            const raw = record.rawRecord;
            if (!raw) {
                continue;
            }
            if (raw.is_secondary) {
                record.colorIndex = SECONDARY_CALENDAR_COLOR_INDEX;
                continue;
            }
            const cci = raw.calendar_color_index;
            if (cci !== undefined && cci !== false && cci !== null) {
                const n = Number(cci);
                if (!Number.isNaN(n)) {
                    record.colorIndex = n;
                }
            }
        }
    },
});

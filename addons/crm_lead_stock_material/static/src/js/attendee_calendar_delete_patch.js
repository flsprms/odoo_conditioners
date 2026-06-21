/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";

/**
 * Standard Odoo deletes only when the current user is both organizer and attendee.
 * With another user's calendar pinned, delete declines that user's attendance
 * (strikethrough) instead of removing the event.
 *
 * If the current user can edit the event, delete it when acting on another
 * attendee's calendar row (pinned user calendar).
 */
patch(AttendeeCalendarController.prototype, {
    deleteRecord(record) {
        const raw = record.rawRecord;
        const organizerPartnerId = raw.partner_id && raw.partner_id[0];
        const isOwnOrganizerEvent =
            user.partnerId === record.attendeeId &&
            user.partnerId === organizerPartnerId;
        const canDeletePinnedUserEvent =
            raw.user_can_edit && user.partnerId !== record.attendeeId;

        if (isOwnOrganizerEvent || canDeletePinnedUserEvent) {
            if (raw.recurrency) {
                this.openRecurringDeletionWizard(record);
            } else {
                CalendarController.prototype.deleteRecord.call(this, record);
            }
            return;
        }

        this.orm
            .call("calendar.attendee", "do_decline", [record.calendarAttendeeId])
            .then(this.model.load.bind(this.model));
    },
});

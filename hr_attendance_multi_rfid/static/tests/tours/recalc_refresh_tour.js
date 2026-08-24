import { registry } from "@web/core/registry";

/**
 * E2E tour - the operator watches a rebuild and presses Refresh.
 *
 * The rebuild runs in the background, so the form does not move on its own
 * and the operator presses Refresh to look again. That press used to WRITE
 * the state of the very record the worker was updating: the two transactions
 * touched the same row, the request lost the race
 * ("could not serialize access due to concurrent update"), and a server error
 * landed on the screen of somebody whose rebuild was running perfectly well.
 *
 * The tour opens a queued rebuild, presses Refresh, and requires the form to
 * still be there afterwards - which it is not if the button raises.
 *
 * Pre-conditions (HttpCase fixture): one queued hr.attendance.recalc.run.
 */
registry.category("web_tour.tours").add("hr_attendance_recalc_refresh_tour", {
    url: "/odoo/action-hr_attendance_multi_rfid.hr_attendance_recalc_run_action",
    steps: () => [
        {
            content: "The list of rebuilds is on screen",
            trigger: ".o_list_view",
        },
        {
            content: "Open the rebuild that is waiting",
            trigger: ".o_data_row:first-child .o_data_cell",
            run: "click",
        },
        {
            content: "The form shows a rebuild that has not started yet",
            trigger: ".o_form_view .o_statusbar_status",
        },
        {
            content: "Press Refresh - looking must never write",
            trigger: "button[name='action_refresh']",
            run: "click",
        },
        {
            content: "The form is still there: no error dialog took over",
            trigger: ".o_form_view button[name='action_refresh']",
        },
        {
            content: "And no error dialog is open",
            trigger: "body:not(:has(.o_error_dialog))",
        },
    ],
});

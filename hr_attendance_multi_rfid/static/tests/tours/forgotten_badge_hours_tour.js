import { registry } from "@web/core/registry";

/**
 * E2E tour - the number of hours a forgotten day is worth, set on a working
 * schedule.
 *
 * On a floating schedule of fourteen hours, a day nobody badged out of should
 * not pay all fourteen. Whoever keeps the schedules opens the list of working
 * schedules, opens the schedule, sees 00:00 (the schedule's own day), types
 * seven hours into "Hours for a Forgotten Badge" and saves; the Python side
 * then reads the stored number back.
 *
 * Pre-conditions (HttpCase fixture): a working schedule "Tour Floating Schedule".
 */
registry.category("web_tour.tours").add("hr_attendance_forgotten_badge_hours_tour", {
    steps: () => [
        {
            content: "Open the schedule from the list of working schedules",
            trigger: ".o_list_view .o_data_row .o_data_cell:contains('Tour Floating Schedule')",
            run: "click",
        },
        {
            content: "Until a number is set, the schedule's own day counts: 00:00",
            trigger: ".o_form_view .o_field_widget[name='forgotten_badge_hours'] input:value(\"00:00\")",
        },
        {
            content: "Type seven hours",
            trigger: ".o_form_view .o_field_widget[name='forgotten_badge_hours'] input",
            run: "edit 07:00",
        },
        {
            content: "Save the schedule",
            trigger: ".o_form_button_save:enabled",
            run: "click",
        },
        {
            content: "The form is saved and still shows seven hours",
            trigger: ".o_form_saved .o_field_widget[name='forgotten_badge_hours'] input:value(\"07:00\")",
        },
    ],
});

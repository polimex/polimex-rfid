import { registry } from "@web/core/registry";

/**
 * E2E tour — review self-leaves (early departures).
 *
 * Process: an attendance officer opens Attendances ▸ Reports ▸ Self-leave,
 * which lists daily roll-ups where the employee left before their scheduled
 * end, grouped by employee. The officer expands an employee and drills into
 * one day to inspect the early-departure time.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one hr.attendance.extra for employee "SelfLeave Tester" with
 *     early_leave_time > 0 (so it matches the pinned [early_leave_time>0]
 *     domain of the action).
 */
registry.category("web_tour.tours").add("hr_self_leave_review_tour", {
    url: "/odoo/action-hr_attendance_late.hr_attendance_self_leave_action",
    steps: () => [
        {
            content: "Self-leave report rendered, grouped by employee",
            trigger: ".o_list_view .o_group_header",
        },
        {
            content: "Expand the employee group",
            trigger: ".o_group_header:contains(SelfLeave Tester)",
            run: "click",
        },
        {
            content: "Open the early-departure day",
            trigger: ".o_data_row .o_data_cell",
            run: "click",
        },
        {
            content: "Form shows the early-departure time field",
            trigger: ".o_form_view .o_field_widget[name='early_leave_time']",
        },
        {
            content: "Employee matches the one we drilled into",
            trigger: ".o_form_view .o_field_widget[name='employee_id']:contains(SelfLeave Tester)",
        },
    ],
});

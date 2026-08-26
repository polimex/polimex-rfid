import { registry } from "@web/core/registry";

/**
 * E2E tour - the extra-calculations report opens on the month that is over.
 *
 * Process: an HR officer opens Attendances > Reporting > Extra calculations to
 * check the month that has just finished. On an installation with years of
 * daily roll-ups behind it, opening everything ever recorded is a minutes-long
 * wait for a screen nobody asked for, so the report opens already narrowed to
 * the previous month; widening it is one click on the Date filter.
 *
 * Pre-conditions (HttpCase fixture):
 *   * "Pivot LastMonth" has one roll-up dated in the previous month;
 *   * "Pivot LongAgo" has one dated six months back.
 * The assertion is therefore about WHO is on the screen, not about the wording
 * of the facet: the first must be there, the second must not.
 */
registry.category("web_tour.tours").add("hr_extra_previous_month_tour", {
    url: "/odoo/action-hr_attendance_late.hr_attendance_extra_action",
    steps: () => [
        {
            content: "The pivot rendered",
            trigger: ".o_pivot_view table",
        },
        {
            content: "A period is already applied - the search bar carries a facet",
            trigger: ".o_searchview .o_facet_values",
        },
        {
            content: "The person with a previous-month roll-up is on the screen",
            trigger: ".o_pivot_view table:contains(Pivot LastMonth)",
        },
        {
            content: "The person whose only roll-up is six months old is not",
            trigger: ".o_pivot_view table:not(:contains(Pivot LongAgo))",
        },
    ],
});

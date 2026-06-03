import { registry } from "@web/core/registry";

/**
 * E2E tour — override a dated legal rate inline.
 *
 * Process: an HR manager opens Attendances ▸ Configuration ▸ Legal Rates
 * (grouped by code), expands a rate's code group, and edits the coefficient
 * for the period — the "override the national value" flow the form's tip
 * describes.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one hr.legal.rate with code "zz_tour_rate" and value 1.5.
 */
registry.category("web_tour.tours").add("hr_legal_rate_edit_tour", {
    url: "/odoo/action-hr_attendance_late.hr_legal_rate_action",
    steps: () => [
        {
            content: "Legal Rates list rendered, grouped by code",
            trigger: ".o_list_view .o_group_header",
        },
        {
            content: "Expand the rate's code group",
            trigger: ".o_group_header:contains(zz_tour_rate)",
            run: "click",
        },
        {
            content: "Enter inline edit on the coefficient cell",
            trigger: ".o_data_row td.o_data_cell[name='value']",
            run: "click",
        },
        {
            content: "Type the new coefficient",
            trigger: ".o_selected_row .o_field_widget[name='value'] input",
            run: "edit 1.85",
        },
        {
            content: "Save the change",
            trigger: ".o_control_panel .o_list_button_save",
            run: "click",
        },
        {
            content: "Saved — the new coefficient is shown",
            trigger: ".o_data_cell:contains(1.85)",
        },
    ],
});

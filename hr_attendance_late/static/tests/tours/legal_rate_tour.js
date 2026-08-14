import { registry } from "@web/core/registry";

/**
 * E2E tour - correct a dated legal coefficient inline.
 *
 * Process: an HR manager opens Attendances - Configuration - Legal Rates
 * (grouped by code), expands a rate's code group, corrects the coefficient
 * for the period and afterwards sees the corrected value on that same rate -
 * the "override the national value" flow the form's tip describes.
 *
 * The coefficient is asserted with a decimal-mark-agnostic pattern
 * (/1[.,]85/). The cell is rendered through the reader's locale, so the very
 * same saved coefficient reads "1.8500" on an English instance and "1,8500"
 * on a Bulgarian one. Matching one formatted string would assert the locale
 * of the test database instead of the manager's correction.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one hr.legal.rate with code "zz_tour_rate" and value 1.5.
 */

// The row of the rate under test, so every assertion speaks about the rate the
// manager edited and not about whatever row happens to be on screen.
const RATE_ROW = ".o_data_row:has(.o_data_cell[name='code']:contains(zz_tour_rate))";

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
            content: "The rate still carries the coefficient to be corrected",
            trigger: `${RATE_ROW} td.o_data_cell[name='value']:contains(/1[.,]5/)`,
        },
        {
            content: "Enter inline edit on the coefficient cell",
            trigger: `${RATE_ROW} td.o_data_cell[name='value']`,
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
            content: "Saved - the edited rate shows the corrected coefficient",
            trigger: `${RATE_ROW} td.o_data_cell[name='value']:contains(/1[.,]85/)`,
        },
        {
            // Negative: the correction must be stored, not left pending on a
            // dirty row - the Save button only exists while a row is in edit.
            content: "Nothing is left unsaved",
            trigger: "body:not(:has(.o_list_button_save))",
        },
    ],
});

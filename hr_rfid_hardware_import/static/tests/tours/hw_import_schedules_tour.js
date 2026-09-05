import { registry } from "@web/core/registry";

/**
 * Narrative 5: two controllers hold different schedules in the same slot.
 * The import is blocked until the operator picks, on the Schedules tab, the
 * controller to take the slot from; then the warning goes away. Selectors
 * use row decorations and the controller's serial, never visible text.
 */
registry.category("web_tour.tours").add("hw_import_schedules_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey with a schedule conflict is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Access groups step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='grouping']",
        },
        {
            content: "The operator is warned that something must be resolved",
            trigger: ".o_form_view .alert-warning",
        },
        {
            content: "The Schedules tab can be opened",
            trigger: ".o_notebook .nav-link[name='schedules']",
            run: "click",
        },
        {
            content: "The conflicting slot stands out",
            trigger: ".o_form_view div[name='ts_slot_ids'] .o_data_row.text-danger",
        },
        {
            content: "The source controller can be chosen inline",
            trigger: ".o_form_view div[name='ts_slot_ids'] .o_data_row.text-danger .o_data_cell[name='source_ctrl_id']",
            run: "click",
        },
        {
            content: "The operator looks for the controller by its serial number",
            trigger: ".o_form_view div[name='ts_slot_ids'] .o_data_row div[name='source_ctrl_id'] input",
            run: "edit 1801",
        },
        {
            content: "The controller is picked from the list",
            trigger: ".o-autocomplete--dropdown-item:contains('1801')",
            run: "click",
        },
        {
            content: "The survey is saved",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "No slot is in conflict any more",
            trigger: ".o_form_view div[name='ts_slot_ids']:not(:has(.o_data_row.text-danger))",
        },
        {
            content: "The warning is gone and the import can start",
            trigger: ".o_form_view:not(:has(.alert-warning))",
        },
    ],
});

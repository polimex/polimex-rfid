import { registry } from "@web/core/registry";

/**
 * Narrative 11: with the controllers read and nothing imported, the operator
 * opens the export dialog, sees the two shapes on offer and the switch for
 * the command log, and walks away. The dialog must be reachable before any
 * import; the download itself is proven by the backend tests. The commands
 * themselves - the proof that only reads were sent - open from the count on
 * the survey.
 */
registry.category("web_tour.tours").add("hw_import_export_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey with the controllers read is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Names step; nothing has been imported",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='naming']",
        },
        {
            content: "The export is offered with its icon",
            trigger: "button[name='action_open_export'] i.fa-download",
            run: "click",
        },
        {
            content: "The dialog offers the shapes of the file",
            trigger: ".modal div[name='file_format'] input[type='radio']",
        },
        {
            content: "The command log can be included on request",
            trigger: ".modal div[name='include_commands'] input[type='checkbox']:not(:checked)",
        },
        {
            content: "The export button is there",
            trigger: ".modal-footer button[name='action_export']",
        },
        {
            content: "The operator walks away without exporting",
            trigger: ".modal-footer button.btn-secondary:not([name])",
            run: "click",
        },
        {
            content: "The dialog is gone and the survey is untouched",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "The commands sent are counted on the survey, not listed inside it",
            trigger: ".o_form_view:not(:has(.o_notebook .nav-link[name='log'])) button[name='action_open_cmd_log'] .o_stat_value",
        },
        {
            content: "The operator opens the command log",
            trigger: "button[name='action_open_cmd_log']",
            run: "click",
        },
        {
            content: "Every command of the survey is a row, with the command that was sent",
            trigger: ".o_list_view .o_data_row td[name='opcode']:contains('F0')",
        },
        {
            content: "The log is for reading only: no New button",
            trigger: ".o_list_view:not(:has(.o_list_button_add))",
        },
        {
            content: "Back to the survey",
            trigger: ".o_breadcrumb .o_back_button",
            run: "click",
        },
        {
            content: "The survey form is back",
            trigger: ".o_form_view button[name='action_open_cmd_log']",
        },
    ],
});

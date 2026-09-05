import { registry } from "@web/core/registry";

/**
 * Narrative 8: the import is done and nothing was sent to the hardware. The
 * module row offers the one explicit device action, "Point to this server",
 * behind a confirmation the operator can still walk away from, and "Enable
 * here" as the step after it. Selectors use icons and names, never text.
 */
registry.category("web_tour.tours").add("hw_import_handover_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The finished survey is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Done step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='done']",
        },
        {
            content: "The operator is told that nothing was sent to the controllers",
            trigger: ".o_form_view .alert-success",
        },
        {
            content: "The modules can be pointed from the header, and the report downloaded",
            trigger: "button[name='action_point_modules']",
        },
        {
            content: "The report is offered",
            trigger: "button[name='action_download_report']",
        },
        {
            content: "The Modules tab can be opened",
            trigger: ".o_notebook .nav-link[name='modules']",
            run: "click",
        },
        {
            content: "The imported module is linked to its record here",
            trigger: ".o_form_view div[name='module_ids'] .o_data_row:contains('4TEST1') td[name='webstack_id']:not(:empty)",
        },
        {
            content: "The module row offers 'Point to this server' with its icon",
            trigger: ".o_form_view div[name='module_ids'] .o_data_row:contains('4TEST1') button[name='action_point_to_server'] i.fa-location-arrow",
            run: "click",
        },
        {
            content: "The action asks for confirmation first",
            trigger: ".modal .modal-footer button.btn-primary",
        },
        {
            content: "The operator can still walk away",
            trigger: ".modal .modal-footer button.btn-secondary",
            run: "click",
        },
        {
            content: "Nothing was sent; the dialog is gone",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "'Enable here' is the step after pointing",
            trigger: ".o_form_view div[name='module_ids'] .o_data_row:contains('4TEST1') button[name='action_enable_module'] i.fa-power-off",
        },
    ],
});

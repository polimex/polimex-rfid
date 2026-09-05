import { registry } from "@web/core/registry";

/**
 * Narrative 1, the last leg: with every finding resolved, the operator opens
 * the import dialog, sees what it will create, starts it and is told the work
 * goes on in the background. Selectors are by name, class and numbers, never
 * by visible text: the database may run in any language.
 */
registry.category("web_tour.tours").add("hw_import_import_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey ready for import is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Access groups step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='grouping']",
        },
        {
            content: "Nothing blocks the import",
            trigger: ".o_form_view:not(:has(.alert-warning))",
        },
        {
            content: "The import dialog opens",
            trigger: "button[name='action_open_import_options']",
            run: "click",
        },
        {
            content: "Every part is ticked by default",
            trigger: ".modal div[name='import_people'] input[type='checkbox']:checked",
        },
        {
            content: "The dialog says how many contacts will be created",
            trigger: ".modal div[name='contact_count']:contains('9')",
        },
        {
            content: "The import is started",
            trigger: ".modal-footer button[name='action_start']",
            run: "click",
        },
        {
            content: "The dialog closes",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "The survey is now importing",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='importing']",
        },
        {
            content: "The operator is told the work goes on in the background",
            trigger: ".o_form_view .alert-info",
        },
        {
            content: "Progress can be checked from here",
            trigger: "button[name='action_refresh']",
        },
    ],
});

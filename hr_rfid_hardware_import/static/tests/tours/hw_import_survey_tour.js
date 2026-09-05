import { registry } from "@web/core/registry";

/**
 * The operator starts a survey and adds a module by address - by typing an
 * address into the dialog and confirming, not by looking at a rendered form.
 * Selectors are by name and class, never by visible text: the database may
 * run in any language.
 */
registry.category("web_tour.tours").add("hw_import_survey_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "A new survey can be started from the list",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "The survey form opens on the Modules step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='draft']",
        },
        {
            content: "A module can be added by address",
            trigger: "button[name='action_add_module']",
            run: "click",
        },
        {
            content: "The address can be typed in",
            trigger: ".modal div[name='ip'] input",
            run: "edit 192.0.2.20",
        },
        {
            content: "What was typed is what the field holds",
            trigger: ".modal div[name='ip'] input:value(192.0.2.20)",
        },
        {
            content: "The module is added and checked",
            trigger: ".modal-footer button[name='action_add']",
            run: "click",
        },
        {
            content: "The dialog closes",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "The module appears in the Modules list with its status",
            trigger: ".o_form_view div[name='module_ids'] .o_data_row:contains('192.0.2.20') .o_field_badge",
        },
        {
            content: "The controllers can be read from here",
            trigger: "button[name='action_read']",
        },
    ],
});

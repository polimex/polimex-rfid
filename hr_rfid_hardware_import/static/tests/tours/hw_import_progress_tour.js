import { registry } from "@web/core/registry";

/**
 * Narrative 9: a long reading runs in the background. The operator opens the
 * survey while it is being read, sees the progress and the module being
 * read, and asks for a fresh look without disturbing anything. Selectors use
 * the statusbar, widgets and the module's serial number, never text.
 */
registry.category("web_tour.tours").add("hw_import_progress_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey being read is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Reading step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='reading']",
        },
        {
            content: "The operator is told the work goes on in the background",
            trigger: ".o_form_view .alert-info",
        },
        {
            content: "A progress bar shows how far it has got",
            trigger: ".o_form_view div[name='progress'] .o_progressbar",
        },
        {
            content: "The current phase is named",
            trigger: ".o_form_view div[name='current_phase']:not(:empty)",
        },
        {
            content: "A fresh look can be asked for",
            trigger: "button[name='action_refresh']",
            run: "click",
        },
        {
            content: "The survey is still being read",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='reading']",
        },
        {
            content: "The Modules tab can be opened",
            trigger: ".o_notebook .nav-link[name='modules']",
            run: "click",
        },
        {
            content: "The module being read shows its reading state",
            trigger: ".o_form_view div[name='module_ids'] .o_data_row:contains('4TEST1') div[name='read_state'] .badge",
        },
    ],
});

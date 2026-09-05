import { registry } from "@web/core/registry";

/**
 * With the controllers read and a names file loaded, the operator opens the
 * survey, goes to the People tab, splits a person the file merged from two
 * lines, opens the names upload dialog and walks away, then continues to the
 * access groups. The split must happen on screen; the dialog must accept a
 * file field.
 */
registry.category("web_tour.tours").add("hw_import_names_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey in the Names step is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Names step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='naming']",
        },
        {
            content: "The People tab can be opened",
            trigger: ".o_notebook .nav-link[name='people']",
            run: "click",
        },
        {
            content: "The person merged from two lines is listed with two cards",
            trigger: ".o_form_view div[name='person_ids'] .o_data_row:contains('Demo Holder One')",
        },
        {
            content: "The merged person offers the Split button",
            trigger: ".o_form_view div[name='person_ids'] .o_data_row:contains('Demo Holder One') button[name='action_split']",
            run: "click",
        },
        {
            content: "The person is now two people, one card each",
            trigger: ".o_form_view div[name='person_ids'] .o_data_row:contains('Demo Holder One'):eq(1)",
        },
        {
            content: "The names upload dialog opens",
            trigger: "button[name='action_upload_names']",
            run: "click",
        },
        {
            content: "The dialog offers a file field",
            // The file input itself is hidden behind the widget's button, so
            // the widget container is what the operator sees.
            trigger: ".modal div[name='file']",
        },
        {
            content: "The operator can walk away without uploading",
            trigger: ".modal-footer button.btn-secondary:not([name])",
            run: "click",
        },
        {
            content: "The dialog is gone",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "The survey continues to the access groups",
            trigger: "button[name='action_to_grouping']",
            run: "click",
        },
        {
            content: "The form is on the Access groups step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='grouping']",
        },
    ],
});

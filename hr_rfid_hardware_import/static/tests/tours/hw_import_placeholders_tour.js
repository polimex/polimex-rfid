import { registry } from "@web/core/registry";

/**
 * Narrative 4: no names file. Every card got a generated owner, a contact by
 * default; the operator turns one of them into an employee from the People
 * list, continues without names, and the import dialog then counts one
 * employee and asks for a department. Selectors avoid visible text.
 */
registry.category("web_tour.tours").add("hw_import_placeholders_tour", {
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
            content: "A generated owner is named after its card",
            trigger: ".o_form_view div[name='person_ids'] .o_data_row:contains('0000100001')",
        },
        {
            content: "The kind of that owner can be edited inline",
            trigger: ".o_form_view div[name='person_ids'] .o_data_row:contains('0000100001') .o_data_cell[name='owner_type']",
            run: "click",
        },
        {
            // In edit mode the name sits in an input, so the row no longer
            // "contains" it as text; the row being edited is the selected one.
            content: "The kind opens as a choice list",
            trigger: ".o_form_view div[name='person_ids'] .o_data_row.o_selected_row div[name='owner_type'] .o_select_menu_toggler",
            run: "click",
        },
        {
            content: "The owner becomes an employee (the second kind offered)",
            trigger: ".o_select_menu_menu .o_select_menu_item[data-choice-index='1']",
            run: "click",
        },
        {
            content: "The survey is saved",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "The survey continues without names",
            trigger: "button[name='action_skip_names']",
            run: "click",
        },
        {
            content: "The form is on the Access groups step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='grouping']",
        },
        {
            content: "The import dialog opens",
            trigger: "button[name='action_open_import_options']",
            run: "click",
        },
        {
            content: "The dialog counts the one employee",
            trigger: ".modal div[name='employee_count']:contains('1')",
        },
        {
            content: "A department is required as soon as anybody is an employee",
            trigger: ".modal div[name='default_department_id'].o_required_modifier",
        },
        {
            content: "The operator walks away without importing",
            trigger: ".modal-footer button.btn-secondary:not([name])",
            run: "click",
        },
        {
            content: "The dialog is gone",
            trigger: "body:not(:has(.modal))",
        },
    ],
});

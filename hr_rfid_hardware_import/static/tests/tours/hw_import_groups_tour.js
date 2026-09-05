import { registry } from "@web/core/registry";

/**
 * On the Access groups step the operator renames a proposed group inline and
 * saves, then opens the merge dialog, reads what it says and walks away. A
 * proposed name that cannot be edited, or a merge nobody can reach from the
 * screen, is exactly the failure this catches.
 */
registry.category("web_tour.tours").add("hw_import_groups_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey in the Access groups step is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Access groups step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='grouping']",
        },
        {
            content: "The Access groups tab can be opened",
            trigger: ".o_notebook .nav-link[name='groups']",
            run: "click",
        },
        {
            content: "A proposed group's name can be edited inline",
            trigger: ".o_form_view div[name='group_ids'] .o_data_row:first .o_data_cell[name='name']",
            run: "click",
        },
        {
            content: "The name accepts typing",
            trigger: ".o_form_view div[name='group_ids'] .o_data_row:first div[name='name'] input",
            run: "edit Front doors",
        },
        {
            content: "The survey is saved with the new name",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "The renamed group is shown",
            trigger: ".o_form_view div[name='group_ids'] .o_data_row:contains('Front doors')",
        },
        {
            content: "The merge dialog can be reached from the tab",
            trigger: "button[name='action_open_group_merge']",
            run: "click",
        },
        {
            content: "The dialog lets the operator pick the groups to merge",
            trigger: ".modal div[name='group_ids']",
        },
        {
            content: "The dialog explains what a merge does before anything is merged",
            // The wording depends on the operator's language; what matters is
            // that the explanation is there before any group is chosen.
            trigger: ".modal div[name='warning']:not(:empty)",
        },
        {
            content: "The operator walks away without merging",
            trigger: ".modal-footer button.btn-secondary:not([name])",
            run: "click",
        },
        {
            content: "The dialog is gone and nothing was merged",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "The import can be started from here",
            trigger: "button[name='action_open_import_options']",
        },
    ],
});

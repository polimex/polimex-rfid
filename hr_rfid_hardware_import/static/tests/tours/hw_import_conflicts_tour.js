import { registry } from "@web/core/registry";

/**
 * Narrative 6: the site was surveyed before, so a module and a card already
 * exist here. Each conflict is a finding that blocks the import until the
 * operator decides, inline on the Findings tab, whether to use the existing
 * record. Selectors use row decorations and the module's serial number.
 */
registry.category("web_tour.tours").add("hw_import_conflicts_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey with conflicts is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Access groups step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='grouping']",
        },
        {
            content: "The operator is warned that findings must be resolved",
            trigger: ".o_form_view .alert-warning",
        },
        {
            content: "The Findings tab can be opened",
            trigger: ".o_notebook .nav-link[name='issues']",
            run: "click",
        },
        {
            content: "The module already registered here is a blocking finding",
            trigger: ".o_form_view div[name='issue_ids'] .o_data_row.text-danger:contains('4TEST1')",
        },
        {
            content: "The decision can be taken inline",
            trigger: ".o_form_view div[name='issue_ids'] .o_data_row:contains('4TEST1') .o_data_cell[name='resolution']",
            run: "click",
        },
        {
            content: "The decision opens as a choice list",
            trigger: ".o_form_view div[name='issue_ids'] .o_data_row:contains('4TEST1') div[name='resolution'] .o_select_menu_toggler",
            run: "click",
        },
        {
            content: "The operator chooses to use the existing record (the second choice offered)",
            trigger: ".o_select_menu_menu .o_select_menu_item[data-choice-index='1']",
            run: "click",
        },
        {
            content: "The survey is saved",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "That finding no longer blocks",
            trigger: ".o_form_view div[name='issue_ids'] .o_data_row:contains('4TEST1'):not(.text-danger)",
        },
        {
            content: "The card already registered here is still to be decided",
            trigger: ".o_form_view div[name='issue_ids'] .o_data_row.text-danger:contains('0000100001')",
        },
    ],
});

import { registry } from "@web/core/registry";

/**
 * Narrative 7: mixed hardware. On the Controllers tab the vending machine is
 * listed but cannot be ticked, the fire panel and the relay controller are
 * read for their settings only, and the access controllers show how many
 * cards were read. Selectors use serial numbers, decorations and counts.
 */
registry.category("web_tour.tours").add("hw_import_hardware_tour", {
    url: "/odoo/action-hr_rfid_hardware_import.hw_import_run_action",
    steps: () => [
        {
            content: "The survey is listed",
            trigger: ".o_list_view .o_data_row .o_field_badge",
            run: "click",
        },
        {
            content: "The form is on the Names step",
            trigger: ".o_form_view .o_statusbar_status button.o_arrow_button_current[data-value='naming']",
        },
        {
            content: "The Controllers tab can be opened",
            trigger: ".o_notebook .nav-link[name='controllers']",
            run: "click",
        },
        {
            content: "The vending machine is listed but greyed out",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row.text-muted:contains('1601')",
        },
        {
            content: "The vending machine cannot be ticked",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row:contains('1601') td[name='include'].o_readonly_modifier",
        },
        {
            content: "An access controller can be ticked",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row:contains('1801') td[name='include']:not(.o_readonly_modifier)",
        },
        {
            content: "The fire panel shows its kind",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row:contains('1802') div[name='family'] .badge",
        },
        {
            content: "The relay controller was read",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row:contains('3101') div[name='read_state'] .badge.text-bg-success",
        },
        {
            content: "The four-reader controller reports its six cards",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row:contains('1801') td[name='cards_read']:contains('6')",
        },
        {
            content: "The two-reader controller reports its five cards",
            trigger: ".o_form_view div[name='ctrl_ids'] .o_data_row:contains('1101') td[name='cards_read']:contains('5')",
        },
    ],
});

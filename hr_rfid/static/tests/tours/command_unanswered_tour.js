import { registry } from "@web/core/registry";

/**
 * E2E tour - read why a command to a controller was not carried out.
 *
 * Process: a security officer opens Commands to Modules, finds the command
 * the controller never answered, sees it marked unsuccessful with the reason,
 * opens it and reads the reason and when it was handed to the module.
 *
 * Pre-conditions (HttpCase fixture): one command for "AGTour Controller",
 * handed over and closed without an answer today.
 */
registry.category("web_tour.tours").add("hr_rfid_command_unanswered_tour", {
    url: "/odoo/action-hr_rfid.hr_rfid_command_action",
    steps: () => [
        {
            content: "The command is listed as unsuccessful, in the colour of a failure",
            trigger:
                ".o_list_view .o_data_row:contains(AGTour Controller) " +
                "td[name='status'].text-danger:contains(Command Execution Unsuccessful)",
        },
        {
            content: "The list says why: the module never answered",
            trigger:
                ".o_list_view .o_data_row:contains(AGTour Controller) " +
                "td[name='error']:contains(No response from the Module)",
        },
        {
            content: "Open the command",
            trigger: ".o_list_view .o_data_row:contains(AGTour Controller) td[name='controller_id']",
            run: "click",
        },
        {
            content: "The form gives the same reason",
            trigger:
                ".o_form_view .o_field_widget[name='error']:contains(No response from the Module)",
        },
        {
            content: "And when the command was handed to the module",
            trigger: ".o_form_view .o_field_widget[name='sent_at']:not(.o_field_empty)",
        },
    ],
});

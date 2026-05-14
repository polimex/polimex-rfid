import { registry } from "@web/core/registry";

/**
 * E2E tour — set up a voting display from scratch.
 *
 * Process: An election admin opens the Voting Displays catalog, clicks
 * New, types a kiosk-friendly name, saves. The display is listed and
 * its short_code / display_url auto-populate via model defaults.
 */
registry.category("web_tour.tours").add("elections_create_display_tour", {
    url: "/odoo/action-hr_rfid_vertical_elections.voting_display_action",
    steps: () => [
        {
            content: "Voting Displays list rendered (may be empty)",
            trigger: ".o_list_view, .o_view_nocontent",
        },
        {
            content: "Click New to create a display",
            trigger: ".o_list_button_add, button.o_list_button_add",
            run: "click",
        },
        {
            content: "Type the display name",
            trigger: ".o_form_view .o_field_widget[name='name'] input",
            run: "edit Tour Polling Kiosk",
        },
        {
            content: "Save the display",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Saved — breadcrumb shows the new display name",
            trigger: ".o_form_view .o_breadcrumb:contains(Tour Polling Kiosk)",
        },
    ],
});

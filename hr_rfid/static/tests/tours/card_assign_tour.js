import { registry } from "@web/core/registry";

/**
 * E2E tour — issue an RFID card to a contact.
 *
 * Process: An admin opens RFID Cards, clicks New, types the 10-digit
 * card number, picks an existing contact as the owner, saves. The new
 * card appears in the list with its owner.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one res.partner named "CardTour Contact A"
 */
registry.category("web_tour.tours").add("hr_rfid_card_assign_tour", {
    url: "/odoo/action-hr_rfid.hr_rfid_card_action",
    steps: () => [
        {
            content: "Cards list view rendered",
            trigger: ".o_list_view, .o_view_nocontent",
        },
        {
            content: "Click New to create a card",
            trigger:
                ".o_control_panel_main_buttons .o_list_button_add, " +
                ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Type the 10-digit card number",
            trigger: ".o_form_view .o_field_widget[name='number'] input",
            run: "edit 8000000123",
        },
        {
            content: "Pick the contact owner",
            trigger: ".o_form_view .o_field_widget[name='contact_id'] input",
            run: "edit CardTour Contact A",
        },
        {
            content: "Confirm contact from autocomplete",
            trigger:
                ".o-autocomplete--dropdown-menu li a:contains(CardTour Contact A)",
            run: "click",
        },
        {
            content: "Save the card",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Saved — breadcrumb shows the card number",
            trigger: ".o_form_view .o_breadcrumb:contains(8000000123)",
        },
    ],
});

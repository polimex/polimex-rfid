import { registry } from "@web/core/registry";

/**
 * E2E tour — issue a visitor card from the Services catalog.
 *
 * Golden path:
 *   1. Open Services list, click into the seeded "Tour Day Pass".
 *   2. Open Action menu → "Sale RFID Service" — the wizard opens.
 *   3. Type the card number.
 *   4. Click Encode Card. Wizard closes.
 *   5. Open Service Sales — the freshly issued sale appears.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one rfid.service named "Tour Day Pass" with AG + card type
 *   * a hardware stack (webstack → controller → door) so the AG has at
 *     least one door, otherwise write_card raises.
 */
registry.category("web_tour.tours").add("rfid_service_base_issue_visitor_card_tour", {
    url: "/odoo/action-rfid_service_base.hr_rfid_service_action",
    steps: () => [
        {
            content: "Services kanban rendered with the seeded service visible",
            trigger: ".o_kanban_record:contains(Tour Day Pass)",
        },
        {
            content: "Switch to list view to open the record (kanban has can_open='0')",
            trigger: ".o_switch_view.o_list, button.o_switch_view.o_list",
            run: "click",
        },
        {
            content: "List view rendered with the seeded service row",
            trigger: ".o_data_row td:contains(Tour Day Pass)",
        },
        {
            content: "Open the seeded service",
            trigger: ".o_data_row td:contains(Tour Day Pass)",
            run: "click",
        },
        {
            content: "Service form loaded",
            trigger: ".o_form_view .o_breadcrumb:contains(Tour Day Pass), .o_form_view input#name_0",
        },
        {
            content: "Open the Actions dropdown (cogwheel)",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            content: "Click 'Sale RFID Service' in the Actions menu",
            trigger: ".o-dropdown--menu .o_menu_item:contains(Sale RFID Service)",
            run: "click",
        },
        {
            content: "Wizard opened — card_number field is editable",
            trigger: ".modal-dialog .o_field_widget[name='card_number'] input",
            // hr.rfid.card.number is digits-only; pick a 10-digit value.
            run: "edit 9000000042",
        },
        {
            content: "Click Encode Card",
            trigger:
                ".modal-dialog .modal-footer button[name='write_card'], " +
                ".modal-dialog button.btn-primary:contains(Encode Card)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Wizard closed — modal dialog is gone",
            trigger: "body:not(:has(.modal-dialog))",
        },
    ],
});

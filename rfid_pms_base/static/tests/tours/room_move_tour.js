import { registry } from "@web/core/registry";

/**
 * E2E tour — drives the receptionist through the room-move workflow:
 *   1. From an occupied room (has reservation), click "Move".
 *   2. Wizard opens; pick the destination room.
 *   3. Submit; the wizard closes. Re-opening the kanban shows the
 *      destination room now carries the reservation.
 *
 * Pre-conditions (HttpCase fixture):
 *   * "Move-Src" — has a contact rel on its AG (reservation is set)
 *   * "Move-Dst" — empty AG, no reservation
 */
registry.category("web_tour.tours").add("rfid_pms_base_room_move_tour", {
    url: "/odoo/action-rfid_pms_base.action_window_room",
    steps: () => [
        {
            content: "Source room visible in kanban",
            trigger:
                ".o_kanban_record:contains(Move-Src), " +
                ".o_data_row:contains(Move-Src)",
        },
        {
            content: "Source room shows Move button (only present when reservation is set)",
            trigger: ".o_kanban_record:contains(Move-Src) button:has(.fa-arrow-right)",
            run: "click",
        },
        {
            content: "Move wizard opened",
            trigger: ".modal-dialog .o_form_view",
        },
        {
            content: "Pick destination room",
            trigger: ".modal-dialog .o_field_widget[name='room_to_id'] input",
            run: "edit Move-Dst",
        },
        {
            content: "Select the Move-Dst entry from the dropdown",
            trigger: ".o-autocomplete--dropdown-item:contains(Move-Dst)",
            run: "click",
        },
        {
            content: "Confirm move",
            trigger: ".modal-dialog .modal-footer button[name='move_customers']",
            run: "click",
        },
        {
            content: "Wizard closed — back on kanban",
            trigger:
                ".o_kanban_view .o_kanban_record:contains(Move-Dst), " +
                ".o_data_row:contains(Move-Dst)",
        },
    ],
});

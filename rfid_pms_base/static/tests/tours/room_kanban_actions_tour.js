import { registry } from "@web/core/registry";

/**
 * E2E tour — drives the receptionist through the Hotel Rooms kanban:
 *   1. Toggle the DND flag on a room → image swaps from off to on.
 *   2. Toggle the Clean flag → image swaps.
 *   3. Click the per-room "Events" button → navigation lands on the
 *      user-events list filtered for that room's door.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one rfid_pms_base.room called "Tour-Room-1" with a door and AG.
 *
 * Odoo's tour engine does not understand the :is() functional pseudo-
 * class, so each candidate selector is listed as its own comma-
 * separated branch.
 */
registry.category("web_tour.tours").add("rfid_pms_base_kanban_actions_tour", {
    url: "/odoo/action-rfid_pms_base.action_window_room",
    steps: () => [
        {
            content: "Kanban rendered with the test room visible",
            trigger:
                ".o_kanban_record:contains(Tour-Room-1), " +
                ".o_data_row:contains(Tour-Room-1)",
        },
        {
            content: "DND is off — clicking the toggle flips it on",
            trigger:
                ".o_kanban_record:contains(Tour-Room-1) button[name='toggle_hotel'] img[alt='DND off']",
            run: "click",
        },
        {
            content: "DND now reported as on",
            trigger:
                ".o_kanban_record:contains(Tour-Room-1) button[name='toggle_hotel'] img[alt='DND']",
        },
        {
            content: "Clean is off — clicking the toggle flips it on",
            trigger:
                ".o_kanban_record:contains(Tour-Room-1) button[name='toggle_hotel'] img[alt='Clean off']",
            run: "click",
        },
        {
            content: "Clean now reported as on",
            trigger:
                ".o_kanban_record:contains(Tour-Room-1) button[name='toggle_hotel'] img[alt='Clean']",
        },
        {
            content: "Click the per-room Events button",
            trigger:
                ".o_kanban_record:contains(Tour-Room-1) button[name='user_events_act']",
            run: "click",
        },
        {
            content: "Navigation landed on hr.rfid.event.user list/kanban",
            trigger:
                ".o_breadcrumb:contains(User Events), " +
                ".o_list_view, " +
                ".o_kanban_view",
        },
    ],
});

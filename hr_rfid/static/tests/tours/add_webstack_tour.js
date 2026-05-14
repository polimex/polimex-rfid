import { registry } from "@web/core/registry";

/**
 * E2E tour — register a new RFID module (webstack) via the Manual
 * Create wizard.
 *
 * Process: An admin opens the Add Module wizard, types the serial
 * number printed on the device, clicks "Add module". A new
 * hr.rfid.webstack row is created.
 *
 * The wizard is also reachable from the webstack list via Actions →
 * "Add Module", but that binding requires record selection. The
 * direct action URL is the canonical entry point Odoo uses.
 *
 * Serial is the only required field; the wizard's onchange auto-fills
 * a friendly name from the serial.
 */
registry.category("web_tour.tours").add("hr_rfid_add_webstack_tour", {
    url: "/odoo/action-hr_rfid.hr_rfid_webstack_manual_create_action",
    steps: () => [
        {
            content: "Wizard opened — type the serial number",
            trigger:
                ".modal-dialog .o_field_widget[name='webstack_serial'] input, " +
                ".o_form_view .o_field_widget[name='webstack_serial'] input",
            run: "edit TOURWS9000042",
        },
        {
            content: "Click 'Add module' to create the webstack",
            trigger:
                ".modal-dialog .modal-footer button[name='create_webstack'], " +
                ".o_form_view button[name='create_webstack']",
            run: "click",
        },
        {
            content: "Wizard closed — Modules view rendered",
            trigger: ".o_kanban_view, .o_list_view",
        },
    ],
});

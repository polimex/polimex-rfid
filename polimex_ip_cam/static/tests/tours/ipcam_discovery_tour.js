/** @odoo-module */
import { registry } from "@web/core/registry";

// Drives the zero-config discover-and-adopt flow. The server-side probe is
// patched to canned results by the HttpCase, so the wizard opens pre-populated:
// the operator drops one device, keeps the other, and adopts it into a camera.
registry.category("web_tour.tours").add("ipcam_discovery_tour", {
    url: "/odoo/action-polimex_ip_cam.action_cctv_camera_discovery",
    steps: () => [
        {
            trigger: ".modal .o_field_x2many td:contains(DS-TCG406-E)",
        },
        {
            trigger: ".modal .o_field_x2many td:contains(AC-9000)",
        },
        {
            // Drop the generic ONVIF device — only the Hikvision one is adopted.
            trigger: ".modal .o_data_row:contains(AC-9000) .o_list_record_remove",
            run: "click",
        },
        {
            trigger: ".modal .o_field_x2many:not(:has(td:contains(AC-9000)))",
        },
        {
            trigger: ".modal button[name='action_create_cameras']",
            run: "click",
        },
        {
            // Adopt succeeded: the wizard closed (the created camera is asserted
            // server-side in the HttpCase — more robust than racing the list nav).
            trigger: "body:not(:has(.modal))",
        },
    ],
});

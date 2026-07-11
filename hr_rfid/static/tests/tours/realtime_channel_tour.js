import { registry } from "@web/core/registry";

/**
 * E2E tour - enable the real-time (Odoo Bus) channel on an RFID module.
 *
 * Process: an operator opens a module's form, presses "Enable real-time"
 * in the Real-time connection section. The channel activates: the button
 * flips to "Disable real-time" and the online status field appears. No
 * device setup is needed - the settings reach the module on its next
 * check-in.
 *
 * The test opens the specific webstack form URL (record id injected by
 * the HttpCase) so the steps start on the form.
 */
registry.category("web_tour.tours").add("hr_rfid_realtime_channel_tour", {
    steps: () => [
        {
            content: "Module form open - press Enable real-time",
            trigger: ".o_form_view button[name='action_ws_enable']",
            run: "click",
        },
        {
            content: "Channel enabled - the Disable button is now shown",
            trigger: ".o_form_view button[name='action_ws_disable']",
        },
        {
            content: "... and the online status field is now visible",
            trigger: ".o_form_view .o_field_widget[name='ws_online']",
        },
    ],
});

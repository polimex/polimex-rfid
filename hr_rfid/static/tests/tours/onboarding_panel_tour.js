import { registry } from "@web/core/registry";

/**
 * E2E tour — the RFID onboarding banner renders natively and is actionable.
 *
 * Process: an admin opens the User Events list on a freshly-set-up system.
 * The standard Odoo onboarding banner is rendered above the list (core
 * markup, not a hand-rolled copy), with a step image, a step title and an
 * actionable button. Clicking the first step's button opens its action
 * (the RFID Settings page).
 *
 * Visual contract: assert the native `o_onboarding_*` markup AND the step
 * image so a CSS/asset regression fails the tour, not just a functional one.
 */
registry.category("web_tour.tours").add("hr_rfid_onboarding_panel_tour", {
    url: "/odoo/action-hr_rfid.hr_rfid_event_user_action",
    steps: () => [
        {
            content: "The native onboarding banner is rendered above the list",
            trigger: ".o_list_view .o_onboarding_main .o_onboarding_steps",
        },
        {
            content: "A step image renders (core onboarding markup + assets)",
            trigger: ".o_onboarding_step .o_onboarding_step_side img",
        },
        {
            content: "The first step exposes a title",
            trigger:
                ".o_onboarding_step:first-child .o_onboarding_step_title",
        },
        {
            content: "Click the 'Create Access Group' step action",
            trigger:
                "a.o_onboarding_step_action[data-method='action_open_step_create_access_group']",
            run: "click",
        },
        {
            content: "The step action opened the Access Group dialog",
            trigger: ".modal-dialog .o_form_view",
        },
    ],
});

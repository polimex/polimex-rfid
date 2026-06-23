import { registry } from "@web/core/registry";

/**
 * E2E tour — the onboarding banner renders above a KANBAN view (the
 * onboarding_kanban renderer variant) and can be dismissed cleanly.
 *
 * Process: a new hotelier opens Hotel Rooms. The native Odoo onboarding
 * banner sits above the rooms kanban. They dismiss it via the close
 * control; the confirmation modal opens, they confirm, and the banner
 * disappears WITHOUT leaving a stuck Bootstrap backdrop.
 */
registry.category("web_tour.tours").add("rfid_pms_base_onboarding_panel_tour", {
    url: "/odoo/action-rfid_pms_base.action_window_room",
    steps: () => [
        {
            content: "Banner renders above the rooms kanban (onboarding_kanban)",
            trigger: ".o_kanban_renderer .o_onboarding_main .o_onboarding_steps, .o_kanban_view .o_onboarding_main",
        },
        {
            content: "A step image renders (core onboarding markup + assets)",
            trigger: ".o_onboarding_step .o_onboarding_step_side img",
        },
        {
            content: "Open the close-confirmation dialog",
            trigger: ".o_onboarding_main .o_onboarding_btn_close",
            run: "click",
        },
        {
            content: "The OWL confirmation dialog is shown",
            trigger: ".o_dialog .modal-content",
        },
        {
            content: "Confirm hiding the onboarding panel",
            trigger: ".o_dialog .modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "The dialog closed and the banner is gone",
            trigger: "body:not(:has(.o_dialog))",
        },
        {
            content: "The rooms kanban no longer shows the onboarding banner",
            trigger: ".o_kanban_view:not(:has(.o_onboarding_main))",
        },
    ],
});

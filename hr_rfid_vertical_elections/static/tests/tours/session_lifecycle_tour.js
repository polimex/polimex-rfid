import { registry } from "@web/core/registry";

/**
 * E2E tour — voting session lifecycle (draft → open).
 *
 * Process: An election admin opens Voting Sessions, creates a session
 * linking participants/display/items, clicks Open Voting and verifies
 * the status moves to "open" with a warning ribbon visible.
 *
 * Closing intentionally not exercised: voting.session.write() resets a
 * "closed" session back to "draft" when vote_ids is empty (legacy
 * behaviour, see voting_session.py write() override). The close path
 * requires real ballots from the RFID kiosk and is covered by
 * controller tests, not by a UI tour.
 *
 * Selectors are language-agnostic — they target `data-value`,
 * widget action `name=`, and the warning ribbon hook (`bg-warning`)
 * rather than translatable visible text.
 *
 * Pre-conditions (HttpCase fixture seeds):
 *   * one voting.display named "Tour Kiosk"
 *   * one voting.participants group named "VoteTour Voters"
 *   * one voting.item named "VoteTour Question"
 */
registry.category("web_tour.tours").add("elections_session_lifecycle_tour", {
    url: "/odoo/action-hr_rfid_vertical_elections.vote_session_action",
    steps: () => [
        {
            content: "Voting Sessions view rendered",
            trigger: ".o_kanban_view, .o_list_view, .o_view_nocontent",
        },
        {
            content: "Click New to create a session",
            trigger:
                ".o_control_panel_main_buttons .o_list_button_add, " +
                ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Type the session name",
            trigger: ".o_form_view .o_field_widget[name='name'] input",
            run: "edit Tour Board Meeting Vote",
        },
        {
            content: "Open the voting items m2m tag autocomplete",
            trigger: ".o_form_view .o_field_widget[name='item_ids'] input",
            run: "edit VoteTour Question",
        },
        {
            content: "Confirm the item from the autocomplete dropdown",
            trigger:
                ".o-autocomplete--dropdown-menu li a:contains(VoteTour Question)",
            run: "click",
        },
        {
            content: "Pick the seeded participant group",
            trigger: ".o_form_view .o_field_widget[name='participant_group_id'] input",
            run: "edit VoteTour Voters",
        },
        {
            content: "Confirm participant group from autocomplete",
            trigger:
                ".o-autocomplete--dropdown-menu li a:contains(VoteTour Voters)",
            run: "click",
        },
        {
            content: "Pick the seeded display",
            trigger: ".o_form_view .o_field_widget[name='display_id'] input",
            run: "edit Tour Kiosk",
        },
        {
            content: "Confirm display from autocomplete",
            trigger:
                ".o-autocomplete--dropdown-menu li a:contains(Tour Kiosk)",
            run: "click",
        },
        {
            content: "Save the draft session",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Saved — statusbar shows Draft",
            trigger:
                ".o_form_view .o_statusbar_status .o_arrow_button[data-value='draft'].o_arrow_button_current",
        },
        {
            content: "Click Open Voting",
            trigger: ".o_form_view button[name='button_open_voting_session']",
            run: "click",
        },
        {
            content: "Status moved to Open — statusbar reflects it",
            trigger:
                ".o_form_view .o_statusbar_status .o_arrow_button[data-value='open'].o_arrow_button_current",
        },
        {
            content: "Warning ribbon (Vote in Progress) visible",
            trigger: ".o_form_view .o_widget_web_ribbon .bg-warning",
        },
    ],
});

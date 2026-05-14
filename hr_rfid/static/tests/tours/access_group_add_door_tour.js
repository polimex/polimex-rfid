import { registry } from "@web/core/registry";

/**
 * E2E tour — create an Access Group and attach a door via the
 * Add Doors wizard.
 *
 * Process: An admin opens Access Groups, clicks New, types a name,
 * saves. The Add Doors stat button (hidden on a new record because
 * `invisible="not id"`) appears once the AG has an id, the admin
 * clicks it, picks the seeded door in the m2m_tags, and confirms.
 * The door now shows in the AG's Doors page.
 *
 * Pre-conditions (HttpCase fixture):
 *   * one webstack + controller + door named "AGTour Door"
 */
registry.category("web_tour.tours").add("hr_rfid_access_group_add_door_tour", {
    url: "/odoo/action-hr_rfid.hr_rfid_access_group_action",
    steps: () => [
        {
            content: "Access Groups view rendered",
            trigger: ".o_list_view, .o_view_nocontent",
        },
        {
            content: "Click New to create an AG",
            trigger:
                ".o_control_panel_main_buttons .o_list_button_add, " +
                ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Type the access group name",
            trigger: ".o_form_view .o_field_widget[name='name'] input",
            run: "edit AGTour Lobby Access",
        },
        {
            content: "Save the access group",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "AG saved — Add Doors stat button is now visible",
            trigger: "#hr_rfid_access_group_add_doors_btn",
            run: "click",
        },
        {
            content: "Wizard opened — focus the door m2m_tags input",
            trigger:
                ".modal-dialog .o_field_widget[name='door_ids'] input",
            run: "edit AGTour Door",
        },
        {
            content: "Pick the seeded door from the autocomplete",
            trigger:
                ".o-autocomplete--dropdown-menu li a:contains(AGTour Door)",
            run: "click",
        },
        {
            content: "Click 'Add Doors' to attach it",
            trigger:
                ".modal-dialog .modal-footer button[name='add_doors'], " +
                ".modal-dialog button.btn-primary:contains(Add Doors)",
            run: "click",
        },
        {
            content: "Wizard closed — Doors page lists the new door",
            trigger:
                ".o_form_view .o_field_widget[name='door_ids'] td:contains(AGTour Door)",
        },
    ],
});

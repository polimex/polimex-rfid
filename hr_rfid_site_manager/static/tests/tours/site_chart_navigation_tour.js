import { registry } from "@web/core/registry";

/**
 * E2E tour — verify the site_chart widget navigation.
 *
 * Pre-conditions (set up by the Python HttpCase):
 *   * an hr.rfid.site named "HQ" with a child "Floor 1".
 *   * the user has access to the site form action.
 *
 * NOTE: tours are sensitive to view-mode order in the action and to the
 * exact CSS that the chosen view emits (list / kanban / hierarchy). The
 * Python wrapper is currently disabled while the selectors are tuned
 * against a fresh DB; the JS lives here as the canonical pattern.
 */
registry.category("web_tour.tours").add("hr_rfid_site_chart_navigation_tour", {
    url: "/odoo/action-hr_rfid_site_manager.hr_rfid_site_action",
    steps: () => [
        {
            content: "Action loaded — at least one site visible",
            trigger: ".o_view_controller :is(.o_data_row, .o_kanban_record, .o_hierarchy_node):contains(HQ)",
        },
        {
            content: "Open HQ form",
            trigger: ".o_view_controller :is(.o_data_row, .o_kanban_record, .o_hierarchy_node):contains(HQ)",
            run: "click",
        },
        {
            content: "Site form shows the site_chart widget",
            trigger: ".o_form_view .o_site_chart",
        },
        {
            content: "Hierarchy lists the child site name",
            trigger: ".o_site_chart_children .site_name a:contains(Floor 1)",
        },
        {
            content: "Clicking the child site name navigates to its form",
            trigger: ".o_site_chart_children .site_name a:contains(Floor 1)",
            run: "click",
        },
        {
            content: "After navigation, name field reads Floor 1",
            trigger: ".o_form_view input.o_input[id^='name']:value(Floor 1)",
        },
    ],
});

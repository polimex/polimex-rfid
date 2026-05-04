import { registry } from "@web/core/registry";

/**
 * E2E tour — drives the user from the Site Manager action through the
 * hierarchy view into the form view of "HQ", checks the site_chart
 * widget rendered the child site name, then clicks the child link to
 * confirm navigation lands on its form.
 *
 * Pre-conditions (HttpCase fixture):
 *   * an hr.rfid.site named "HQ" with no parent
 *   * a child site named "Floor 1" with parent_id = HQ
 *
 * The action ships with view_mode="hierarchy,list,form", so the
 * landing view is hierarchy. Odoo's tour engine does not understand
 * the CSS :is() functional pseudo-class, so each candidate selector
 * is listed as its own comma-separated branch.
 */
registry.category("web_tour.tours").add("hr_rfid_site_chart_navigation_tour", {
    url: "/odoo/action-hr_rfid_site_manager.hr_rfid_site_action",
    steps: () => [
        {
            content: "Hierarchy view rendered with HQ visible",
            trigger:
                ".o_hierarchy_node:contains(HQ), " +
                ".o_kanban_record:contains(HQ), " +
                ".o_data_row td:contains(HQ)",
        },
        {
            content: "Open HQ form",
            trigger:
                ".o_hierarchy_node:contains(HQ), " +
                ".o_kanban_record:contains(HQ), " +
                ".o_data_row:contains(HQ)",
            run: "click",
        },
        {
            content: "Form view loaded — site_chart widget rendered",
            trigger: ".o_form_view .o_site_chart",
        },
        {
            content: "site_chart lists the Floor 1 child link",
            trigger: ".o_site_chart_children .site_name a:contains(Floor 1)",
        },
        {
            content: "Click the child link",
            trigger: ".o_site_chart_children .site_name a:contains(Floor 1)",
            run: "click",
        },
        {
            content: "Navigation succeeded — Floor 1 form is showing",
            trigger:
                ".o_form_view input[id^='name'][value='Floor 1'], " +
                ".o_form_view .o_breadcrumb:contains(Floor 1)",
        },
    ],
});

import { registry } from "@web/core/registry";

/**
 * Walks the Dashboards app: renders the Access Control board, verifies its
 * figures actually draw (scorecards + charts in the DOM - the o-spreadsheet
 * renderer is client-side, so only a browser test can prove this), then
 * NAVIGATES to the second (Security and Devices) board and verifies it too.
 * Selectors are language-agnostic (no visible-text matching).
 */
registry.category("web_tour.tours").add("spreadsheet_dashboard_hr_rfid_tour", {
    url: "/odoo/dashboards",
    steps: () => [
        {
            content: "dashboard sidebar is present",
            trigger: ".o_search_panel, .o_spreadsheet_dashboard_search_panel",
        },
        {
            content: "open the first (Access Control) board",
            trigger: ".o_search_panel ul.o_search_panel_field li.o_search_panel_category_value:first-child",
            run: "click",
        },
        {
            content: "spreadsheet canvas mounts",
            trigger: ".o-spreadsheet",
        },
        {
            content: "figures render (scorecards + charts)",
            trigger: ".o-figure",
        },
        {
            content: "at least one chart canvas draws",
            trigger: ".o-figure canvas",
        },
        {
            content: "navigate to the second (Security and Devices) board",
            trigger: ".o_search_panel ul.o_search_panel_field li.o_search_panel_category_value:nth-child(2)",
            run: "click",
        },
        {
            content: "security board figures render",
            trigger: ".o-figure canvas",
        },
    ],
});

import { registry } from "@web/core/registry";

/**
 * E2E tour - find a person's access events by typing the name.
 *
 * Process: a security officer opens User Events, types part of a person's
 * name in the search box and presses Enter - the box's first option, the
 * event's name. The list keeps that person's event and drops another's.
 *
 * Pre-conditions (HttpCase fixture): employees "SearchTour Petrova" and
 * "SearchTour Kolev", one event each, today.
 */
registry.category("web_tour.tours").add("hr_rfid_event_search_by_name_tour", {
    url: "/odoo/action-hr_rfid.hr_rfid_event_user_action",
    steps: () => [
        {
            content: "Today's events of both people are listed",
            trigger: ".o_list_view .o_data_row:contains(SearchTour Kolev)",
        },
        {
            content: "Type part of one person's name in the search box",
            trigger: "input.o_searchview_input",
            run: "edit Petrova",
        },
        {
            content: "Search with the first option, as Enter does",
            trigger: "input.o_searchview_input",
            run: "press Enter",
        },
        {
            content: "The search is applied as a facet",
            trigger: ".o_searchview_facet:contains(Petrova)",
        },
        {
            content: "Only that person's event is left",
            trigger:
                ".o_list_view:not(:has(.o_data_row:contains(SearchTour Kolev))) " +
                ".o_data_row:contains(SearchTour Petrova)",
        },
    ],
});

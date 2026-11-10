import { registry } from "@web/core/registry";

/**
 * E2E tour - find a product's sales by typing its name.
 *
 * Process: a vending operator opens Vending Events (today's sales by
 * default), types part of a product's name in the search box and presses
 * Enter - the box's first option, the event's name, which for a sale reads
 * "product - buyer". The list keeps that product's sale and drops the other.
 *
 * Pre-conditions (HttpCase fixture): sales of "SearchTour Cola" and
 * "SearchTour Water" to one buyer, today.
 */
registry.category("web_tour.tours").add("hr_rfid_vending_event_search_by_product_tour", {
    url: "/odoo/action-hr_rfid_vending.hr_rfid_vending_event_action",
    steps: () => [
        {
            content: "Today's sales of both products are listed",
            trigger: ".o_list_view .o_data_row:contains(SearchTour Water)",
        },
        {
            content: "Type part of one product's name in the search box",
            trigger: "input.o_searchview_input",
            run: "edit Cola",
        },
        {
            content: "Search with the first option, as Enter does",
            trigger: "input.o_searchview_input",
            run: "press Enter",
        },
        {
            content: "The search is applied as a facet",
            trigger: ".o_searchview_facet:contains(Cola)",
        },
        {
            content: "Only that product's sale is left",
            trigger:
                ".o_list_view:not(:has(.o_data_row:contains(SearchTour Water))) " +
                ".o_data_row:contains(SearchTour Cola)",
        },
    ],
});

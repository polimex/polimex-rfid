/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ListController } from "@web/views/list/list_controller";
import { OnboardingBanner } from "../../components/onboarding/onboarding";

/**
 * Make the onboarding banner available to every list and kanban.
 *
 * The banner used to be a view class of its own (js_class="onboarding_list").
 * A view carries exactly ONE js_class, so the moment a second module wanted one
 * on the same view the banner lost: hr_rfid_refresh_views inherits the User
 * Events list and writes js_class="list_refresh_view" over it, and because that
 * module is auto_install it is on nearly every database. The banner component
 * was then never created at all - no error, no request, no banner. It cost a
 * long hunt to find, because the server side rendered the panel perfectly and
 * the browser simply never asked for it.
 *
 * Keying on the action context instead removes the conflict entirely: a view
 * can have any js_class it likes and still show the banner. The template below
 * extends the stock list and kanban, and the banner stays inert unless the
 * action asks for it:
 *
 *     context="{'onboarding_route_name': '<route_name of the onboarding>'}"
 *
 * This departs from Odoo's own habit - core sale ships sale_onboarding_list as
 * a js_class (addons/sale/views/sale_order_views.xml:235) and composes by
 * chaining view classes (sale_onboarding_list extends sale_file_upload_list).
 * Chaining works while one module owns the view; it does not scale to a banner
 * shared by six modules that must each combine with whatever else the view
 * already carries.
 *
 * Registering the component on the stock controllers is what lets the extended
 * template resolve <OnboardingBanner/>; it is otherwise inert.
 */
ListController.components = {
    ...ListController.components,
    OnboardingBanner,
};

KanbanController.components = {
    ...KanbanController.components,
    OnboardingBanner,
};

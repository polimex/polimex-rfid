/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { OnboardingBanner } from "../../components/onboarding/onboarding";

/**
 * Generic list view that renders an onboarding banner above the list.
 *
 * Enable it on any action with:
 *     js_class="onboarding_list"
 *     context="{'onboarding_route_name': '<route_name of the onboarding>'}"
 *
 * The banner is hosted here (hr_rfid) and reused by every module that
 * depends on hr_rfid. Modules that do not depend on hr_rfid ship a
 * namespaced copy of this trio to avoid registry-key collisions.
 */
export class OnboardingListController extends ListController {
    static template = "hr_rfid.OnboardingListView";
    static components = { ...ListController.components, OnboardingBanner };

    get onboardingRouteName() {
        return this.props.context.onboarding_route_name;
    }
}

export const onboardingListView = {
    ...listView,
    Controller: OnboardingListController,
};

registry.category("views").add("onboarding_list", onboardingListView);

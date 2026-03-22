/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { RfidOnboardingBanner } from "../../components/onboarding/onboarding";

export class RfidOnboardingListController extends ListController {
    static template = "hr_rfid.RfidOnboardingListView";
    static components = { ...ListController.components, RfidOnboardingBanner };
}

export const rfidOnboardingListView = {
    ...listView,
    Controller: RfidOnboardingListController,
};

registry.category("views").add("rfid_onboarding_list", rfidOnboardingListView);

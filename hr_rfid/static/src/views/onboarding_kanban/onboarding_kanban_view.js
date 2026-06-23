/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { OnboardingBanner } from "../../components/onboarding/onboarding";

/**
 * Generic kanban view that renders an onboarding banner above the kanban.
 *
 * Counterpart of `onboarding_list` for actions whose default view is kanban.
 * Enable it with:
 *     js_class="onboarding_kanban"
 *     context="{'onboarding_route_name': '<route_name of the onboarding>'}"
 */
export class OnboardingKanbanController extends KanbanController {
    static template = "hr_rfid.OnboardingKanbanView";
    static components = { ...KanbanController.components, OnboardingBanner };

    get onboardingRouteName() {
        return this.props.context.onboarding_route_name;
    }
}

export const onboardingKanbanView = {
    ...kanbanView,
    Controller: OnboardingKanbanController,
};

registry.category("views").add("onboarding_kanban", onboardingKanbanView);

/** @odoo-module **/

import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";
import {useBusRefresh} from "@refresh_mixin/js/use_bus_refresh";

class KanbanRefreshController extends kanbanView.Controller {
    setup() {
        super.setup();
        useBusRefresh({resModel: this.props.resModel, model: this.model});
    }
}

registry.category("views").add("kanban_refresh_view", {
    ...kanbanView,
    Controller: KanbanRefreshController,
});

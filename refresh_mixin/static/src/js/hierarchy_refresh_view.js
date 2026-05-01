/** @odoo-module **/

import {hierarchyView} from "@web_hierarchy/hierarchy_view";
import {registry} from "@web/core/registry";
import {useBusRefresh} from "@refresh_mixin/js/use_bus_refresh";

class HierarchyRefreshController extends hierarchyView.Controller {
    setup() {
        super.setup();
        // Hierarchy view: visible-id matching across the tree is unreliable,
        // so always reload on update if the view is alive.
        useBusRefresh({
            resModel: this.props.resModel,
            model: this.model,
            reloadOnAnyChange: true,
        });
    }
}

registry.category("views").add("hierarchy_refresh_view", {
    ...hierarchyView,
    Controller: HierarchyRefreshController,
});

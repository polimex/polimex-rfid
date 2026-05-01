/** @odoo-module **/

import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";
import {useBusRefresh} from "@refresh_mixin/js/use_bus_refresh";

class ListRefreshController extends listView.Controller {
    setup() {
        super.setup();
        useBusRefresh({resModel: this.props.resModel, model: this.model});
    }
}

registry.category("views").add("list_refresh_view", {
    ...listView,
    Controller: ListRefreshController,
});

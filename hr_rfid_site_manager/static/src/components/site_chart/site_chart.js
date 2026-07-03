/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { onWillStart, useState, onWillUpdateProps, Component } from "@odoo/owl";

export class SiteChart extends Component {
    setup() {
        super.setup();

        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            hierarchy: {},
        });
        onWillStart(async () => await this.fetchHierarchy(this.props.record.resId));

        onWillUpdateProps(async (nextProps) => {
            await this.fetchHierarchy(nextProps.record.resId);
        });
    }

    async fetchHierarchy(siteId) {
        this.state.hierarchy = await this.orm.call("hr.rfid.site", "get_site_hierarchy", [
            siteId,
        ]);
    }

    async openSiteDoors(siteId) {
        const action = await this.orm.call("hr.rfid.site", "open_door_list_action", [[siteId]]);
        await this.action.doAction(action);
    }

    async openSite(siteId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.rfid.site",
            res_id: siteId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
SiteChart.template = "hr_rfid_site_manager.SiteChart";
SiteChart.props = {
    ...standardWidgetProps,
};

export const siteChart = {
    component: SiteChart,
};
registry.category("view_widgets").add("site_chart", siteChart);

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
        console.log(this.state.hierarchy);
    }

    openSiteDoors(siteId) {
        return;
        this.action.doAction("hr_rfid.hr_rfid_door_action", {
            additionalContext: {
                active_id: siteId,
            },
        });
    }
    openSite(siteId) {
        return;
        this.action.doAction("hr_rfid_site_manager.act_site_from_sites", {
            additionalContext: {
                active_id: siteId,
            },
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

/** @odoo-module **/

import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { registry } from "@web/core/registry";
import { status, useComponent, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class HierarchyRefreshController extends hierarchyView.Controller {
    setup() {
        super.setup();

        const component = useComponent();
        const busService = useService("bus_service");
        const channelName = `polimex.${this.props.resModel}`;
        this.isLoading = false;

        // Bind callbacks
        this.onRecordUpdate = this._onRecordUpdate.bind(this);
        this.onRecordCreate = this._onRecordCreate.bind(this);

        // Subscribe to bus
        busService.addChannel(channelName);
        busService.subscribe(channelName + '.record_changed', this.onRecordUpdate);
        busService.subscribe(channelName + '.record_created', this.onRecordCreate);

        // Cleanup on destroy
        onWillDestroy(() => {
            busService.unsubscribe(channelName + '.record_changed', this.onRecordUpdate);
            busService.unsubscribe(channelName + '.record_created', this.onRecordCreate);
            busService.deleteChannel(channelName);
        });

        // Store component reference for status checks
        this.component = component;
    }

    async _onRecordCreate(payload) {
        const isHierarchyView = true;
        const isSameCompany = this.model.env.searchModel.env.services.company.activeCompanyIds.includes(payload.company_id);
        const isViewVisible = status(this.component) !== "destroyed";

        if (isHierarchyView && isSameCompany && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }

    async _onRecordUpdate(payload) {
        const isHierarchyView = true;
        const isIdVisible = this.model.root.trees.flatMap(tree => tree.forest.resIds).includes(payload.record_ids[0]);
        const isViewVisible = status(this.component) !== "destroyed";

        if (isHierarchyView && isIdVisible && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }
}

const RefreshHierarchyView = {
    ...hierarchyView,
    Controller: HierarchyRefreshController,
};
registry.category("views").add("hierarchy_refresh_view", RefreshHierarchyView);
/** @odoo-module **/

import { hierarchyView } from "@web_hierarchy/hierarchy_view";
import { registry } from "@web/core/registry";

class HierarchyRefreshController extends hierarchyView.Controller {
    setup() {
        super.setup();
        this.busService = this.env.services.bus_service;
        const channelName = `polimex.${this.props.resModel}`;
        this.isLoading = false;
        // console.log("HierarchyRefreshController channelName", channelName);
        this.busService.addChannel(channelName);
        this.busService.subscribe(channelName+'.record_changed', this._onRecordUpdate.bind(this));
        this.busService.subscribe(channelName+'.record_created', this._onRecordCreate.bind(this));
        this.env.services.bus_service.start();
    }

    async _onRecordCreate(payload) {
        // console.log("HierarchyRefreshController Create payload", payload);
        const isHierarchyView = true;
        // const isHierarchyView = this.model.action.currentController.view.type == 'hierarchy';
        const isSameCompany = this.model.env.searchModel.env.services.company.activeCompanyIds.includes(payload.company_id);
        const isViewVisible = [0,1].includes(this.__owl__.status);
        if (isHierarchyView && isSameCompany && isViewVisible && !this.isLoading) {
            // console.log("HierarchyRefreshController doing Create with payload", payload, this.model);
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }

    async _onRecordUpdate(payload) {
        console.log("HierarchyRefreshController Update payload", payload, this);
        const isHierarchyView = true;
        // const isHierarchyView = this.model.action.currentController.view.type == 'hierarchy';
        const isIdVisible = this.model.root.trees.flatMap(tree => tree.forest.resIds).includes(payload.record_ids[0]);
        const isViewVisible = [0,1].includes(this.__owl__.status);
        if (isHierarchyView && isIdVisible && isViewVisible && !this.isLoading) {
            // console.log("HierarchyRefreshController Doing Update with payload", payload, this.model);
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

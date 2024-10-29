/** @odoo-module **/

import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

class KanbanRefreshController extends kanbanView.Controller {
    setup() {
        super.setup();
        this.busService = this.env.services.bus_service;
        const channelName = `polimex.${this.props.resModel}`;
        this.isLoading = false;
        // console.log("KanbanRefreshController channelName", channelName);
        this.busService.addChannel(channelName);
        this.busService.subscribe(channelName+'.record_changed', this._onRecordUpdate.bind(this));
        this.busService.subscribe(channelName+'.record_created', this._onRecordCreate.bind(this));
        this.env.services.bus_service.start();
    }

    async _onRecordCreate(payload) {
        // console.log("KanbanRefreshController Create payload", payload);
        const isKanbanView = this.model.action.currentController.view.type == 'kanban';
        const isSameCompany = this.model.config.currentCompanyId == payload.company_id;
        // const isSameModel = this.model.action.currentController.action.res_model == payload.model;
        const isViewVisible = [0,1].includes(this.__owl__.status);
        if (isKanbanView && isSameCompany && isViewVisible && !this.isLoading) {
            // console.log("KanbanRefreshController doing Create with payload", payload, this.model);
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }

    async _onRecordUpdate(payload) {
        // console.log("KanbanRefreshController Update payload", payload);
        const isKanbanView = this.model.action.currentController.view.type == 'kanban';
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        const isViewVisible = [0,1].includes(this.__owl__.status);
        // const isSameModel = this.model.action.currentController.action.res_model == payload.model;
        if (isKanbanView && isIdVisible && isViewVisible && !this.isLoading) {
            // console.log("KanbanRefreshController Doing Update with payload", payload, this.model);
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }

    }

    // async _onRecordUpdate(payload) {
    //     // console.log("KanbanRefreshController payload", payload, this.model);
    //     //this.config.currentCompanyId
    //     //this.model.action.currentController.view.type == 'kanban'
    //     // this.model.root.records.map(obj => obj.resId);
    //     debugger;
    //     if ((this.model.action.currentController.view.type == 'kanban') && (this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0])))
    //         this.model.load();
    //     // if (payload.record_ids) {
    //     //         for (const recordId of payload.record_ids) {
    //     //             await this._refreshSingleRecord(recordId);
    //     //         }
    //     //     }
    // }
}

const RefreshKanbanView = {
    ...kanbanView,
    Controller: KanbanRefreshController,
};
registry.category("views").add("kanban_refresh_view", RefreshKanbanView);

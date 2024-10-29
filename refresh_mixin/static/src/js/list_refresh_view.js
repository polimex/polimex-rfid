/** @odoo-module **/

import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";
import {status} from "@odoo/owl"

class ListRefreshController extends listView.Controller {
    setup() {
        super.setup();
        this.busService = this.env.services.bus_service;
        const channelName = `polimex.${this.props.resModel}`;
        this.isLoading = false;
        // console.log("ListRefreshController channelName", channelName);
        this.busService.addChannel(channelName);
        this.busService.subscribe(channelName+'.record_changed', this._onRecordUpdate.bind(this));
        this.busService.subscribe(channelName+'.record_created', this._onRecordCreate.bind(this));
        this.env.services.bus_service.start();
    }

    async _onRecordUpdate(payload) {
        // console.log("ListRefreshController Update payload", payload);
        const isListView = this.model.action.currentController.view.type == 'list';
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        const isViewVisible = [0,1].includes(this.__owl__.status);
        // const isSameModel = this.model.action.currentController.action.res_model == payload.model;
        if (isListView && isIdVisible && isViewVisible && !this.isLoading) {
            // console.log("ListRefreshController doing Update with payload", payload, this.model);
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }
    async _onRecordCreate(payload) {
        // console.log("ListRefreshController Create payload", payload, this);
        const isListView = this.model.action.currentController.view.type == 'list';
        // const isSameCompany = this.userService.context.allowed_company_ids.includes(payload.company_id);
        const isSameCompany = this.model.config.currentCompanyId == payload.company_id;
        const isViewVisible = [0,1].includes(this.__owl__.status);
        // const isSameModel = this.model.action.currentController.action.res_model == payload.model;
        if (isListView && isSameCompany && isViewVisible && !this.isLoading) {
            // console.log("ListRefreshController doing Create with payload", payload, this.model);
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

const RefreshListView = {
    ...listView,
    Controller: ListRefreshController,
};
registry.category("views").add("list_refresh_view", RefreshListView);

/** @odoo-module **/

import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";

class ListRefreshController extends listView.Controller {
    setup() {
        super.setup();
        this.busService = this.env.services.bus_service;
        const channelName = `polimex.${this.props.resModel}`;
        // console.log("KanbanRefreshController channelName", channelName);
        this.busService.addChannel(channelName);
        this.busService.subscribe('record_changed', this._onRecordUpdate.bind(this));
        this.busService.subscribe('record_created', this._onRecordCreate.bind(this));
        this.env.services.bus_service.start();
    }

    async _onRecordUpdate(payload) {
        const isListView = this.model.action.currentController.view.type == 'list';
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        if (isListView && isIdVisible) {
            console.log("ListRefreshController Update payload", payload, this.model);
            this.model.load();
        }
    }
    async _onRecordCreate(payload) {
        const isListView = this.model.action.currentController.view.type == 'list';
        const isSameCompany = this.model.action.currentController.modelName == payload.model;
        if (isListView && isSameCompany) {
            console.log("ListRefreshController Create payload", payload, this.model);
            this.model.load();
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
registry.category("views").add("hr_rfid_list_refresh_view", RefreshListView);

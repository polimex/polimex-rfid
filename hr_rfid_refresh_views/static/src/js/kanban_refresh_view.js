/** @odoo-module **/

import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

class KanbanRefreshController extends kanbanView.Controller {
    setup() {
        super.setup();
        this.busService = this.env.services.bus_service;
        const channelName = `polimex.${this.props.resModel}`;
        // console.log("KanbanRefreshController channelName", channelName);
        this.busService.addChannel(channelName);
        this.busService.subscribe('record_changed', this._onRecordUpdate.bind(this));
        this.env.services.bus_service.start();
    }

    async _onRecordUpdate(payload) {
        const isKanbanView = this.model.action.currentController.view.type == 'kanban';
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        if (isKanbanView && isIdVisible) {
            console.log("KanbanRefreshController Update payload", payload, this.model);
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

const RefreshKanbanView = {
    ...kanbanView,
    Controller: KanbanRefreshController,
};
registry.category("views").add("hr_rfid_kanban_refresh_view", RefreshKanbanView);

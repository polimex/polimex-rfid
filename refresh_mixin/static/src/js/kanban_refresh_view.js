/** @odoo-module **/

import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { status, useComponent, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class KanbanRefreshController extends kanbanView.Controller {
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
        const isKanbanView = this.model.action.currentController.view.type == 'kanban';
        const isSameCompany = this.model.config.currentCompanyId == payload.company_id;
        const isViewVisible = status(this.component) !== "destroyed";

        if (isKanbanView && isSameCompany && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }

    async _onRecordUpdate(payload) {
        const isKanbanView = this.model.action.currentController.view.type == 'kanban';
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        const isViewVisible = status(this.component) !== "destroyed";

        if (isKanbanView && isIdVisible && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }
}

const RefreshKanbanView = {
    ...kanbanView,
    Controller: KanbanRefreshController,
};
registry.category("views").add("kanban_refresh_view", RefreshKanbanView);
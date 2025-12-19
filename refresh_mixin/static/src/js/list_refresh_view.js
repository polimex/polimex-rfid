/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { status, useComponent, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ListRefreshController extends listView.Controller {
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

    async _onRecordUpdate(payload) {
        const isListView = this.model.action.currentController.view.type == 'list';
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        const isViewVisible = status(this.component) !== "destroyed";

        if (isListView && isIdVisible && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }

    async _onRecordCreate(payload) {
        const isListView = this.model.action.currentController.view.type == 'list';
        const isSameCompany = this.model.config.currentCompanyId == payload.company_id;
        const isViewVisible = status(this.component) !== "destroyed";

        if (isListView && isSameCompany && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }
}

const RefreshListView = {
    ...listView,
    Controller: ListRefreshController,
};
registry.category("views").add("list_refresh_view", RefreshListView);
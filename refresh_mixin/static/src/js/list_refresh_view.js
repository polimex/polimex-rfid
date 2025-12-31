/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { status, useComponent, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

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
        // Check if the updated record is visible in current list
        const isIdVisible = this.model.root.records.map(obj => obj.resId).includes(payload.record_ids[0]);
        const isViewVisible = status(this.component) !== "destroyed";

        if (isIdVisible && isViewVisible && !this.isLoading) {
            this.isLoading = true;
            await this.model.load();
            this.isLoading = false;
        }
    }

    async _onRecordCreate(payload) {
        // Check if notification is for the same company (companies have refresh restrictions)
        const currentCompanyId = user.activeCompany?.id;
        const isSameCompany = !payload.company_id || currentCompanyId == payload.company_id;
        const isViewVisible = status(this.component) !== "destroyed";

        if (isSameCompany && isViewVisible && !this.isLoading) {
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
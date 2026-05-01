/** @odoo-module **/

import {onWillDestroy, status, useComponent} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";

/**
 * Subscribe a view controller to the `polimex.<resModel>` bus channel and reload
 * its model when records change or are created. Returns nothing — meant to be
 * called from a controller `setup()`.
 *
 * Behaviour:
 *  - record_changed: reload only when one of the visible records is affected
 *    (or always, when `reloadOnAnyChange` is true — for hierarchy where
 *    visible-id matching is unreliable across the tree).
 *  - record_created: reload when the active company matches the payload.
 *
 * Concurrent notifications are serialized through a single in-flight Promise
 * so a burst of bus events triggers at most one extra reload after the
 * current one completes.
 */
export function useBusRefresh({resModel, model, reloadOnAnyChange = false}) {
    const component = useComponent();
    const busService = useService("bus_service");
    const channelName = `polimex.${resModel}`;

    const state = {inFlight: null, pending: false};

    const isAlive = () => status(component) !== "destroyed";

    const reload = async () => {
        if (state.inFlight) {
            state.pending = true;
            return;
        }
        try {
            state.inFlight = model.load();
            await state.inFlight;
        } finally {
            state.inFlight = null;
            if (state.pending && isAlive()) {
                state.pending = false;
                await reload();
            }
        }
    };

    const onRecordUpdate = (payload) => {
        if (!isAlive()) {
            return;
        }
        if (reloadOnAnyChange) {
            reload();
            return;
        }
        const visibleIds = model.root.records.map((r) => r.resId);
        if (visibleIds.includes(payload.record_ids?.[0])) {
            reload();
        }
    };

    const onRecordCreate = (payload) => {
        if (!isAlive()) {
            return;
        }
        const sameCompany =
            !payload.company_id || user.activeCompany?.id === payload.company_id;
        if (sameCompany) {
            reload();
        }
    };

    busService.addChannel(channelName);
    busService.subscribe(`${channelName}.record_changed`, onRecordUpdate);
    busService.subscribe(`${channelName}.record_created`, onRecordCreate);

    onWillDestroy(() => {
        busService.unsubscribe(`${channelName}.record_changed`, onRecordUpdate);
        busService.unsubscribe(`${channelName}.record_created`, onRecordCreate);
        busService.deleteChannel(channelName);
    });
}

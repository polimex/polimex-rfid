/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {Component, useState, xml} from "@odoo/owl";
import {
    asyncStep,
    mockService,
    mountWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import {useBusRefresh} from "@refresh_mixin/js/use_bus_refresh";

class FakeModel {
    constructor() {
        this.loadCount = 0;
        this.root = {records: [{resId: 11}, {resId: 12}]};
    }
    async load() {
        this.loadCount += 1;
        asyncStep("load");
    }
}

class HostComponent extends Component {
    static template = xml`<div class="host"/>`;
    static props = ["resModel", "model", "reloadOnAnyChange?"];
    setup() {
        this.state = useState({});
        useBusRefresh({
            resModel: this.props.resModel,
            model: this.props.model,
            reloadOnAnyChange: this.props.reloadOnAnyChange,
        });
    }
}

/**
 * Mock the bus_service in-process so tests can dispatch handlers directly
 * without spinning up the real WebSocket worker. Pattern adapted from
 * Odoo core's mockService("bus_service", ...) usage.
 */
function mockBusService() {
    const handlers = new Map();
    mockService("bus_service", {
        addChannel() {},
        deleteChannel() {},
        subscribe(eventName, callback) {
            if (!handlers.has(eventName)) {
                handlers.set(eventName, new Set());
            }
            handlers.get(eventName).add(callback);
        },
        unsubscribe(eventName, callback) {
            handlers.get(eventName)?.delete(callback);
        },
        _dispatch(eventName, payload) {
            for (const cb of handlers.get(eventName) || []) {
                cb(payload);
            }
        },
    });
    return handlers;
}

test("record_changed triggers reload only when visible id matches", async () => {
    mockBusService();
    const model = new FakeModel();
    const env = await mountWithCleanup(HostComponent, {
        props: {resModel: "hr.rfid.card", model},
    });

    env.services.bus_service._dispatch("polimex.hr.rfid.card.record_changed", {
        record_ids: [99],
    });
    expect(model.loadCount).toBe(0);

    env.services.bus_service._dispatch("polimex.hr.rfid.card.record_changed", {
        record_ids: [12],
    });
    await waitForSteps(["load"]);
    expect(model.loadCount).toBe(1);
});

test("record_created skips when payload company_id differs", async () => {
    mockBusService();
    const model = new FakeModel();
    const env = await mountWithCleanup(HostComponent, {
        props: {resModel: "hr.rfid.card", model},
    });

    env.services.bus_service._dispatch("polimex.hr.rfid.card.record_created", {
        company_id: 99999,
    });
    expect(model.loadCount).toBe(0);
});

test("reloadOnAnyChange forces reload regardless of visible ids", async () => {
    mockBusService();
    const model = new FakeModel();
    const env = await mountWithCleanup(HostComponent, {
        props: {resModel: "hr.rfid.site", model, reloadOnAnyChange: true},
    });

    env.services.bus_service._dispatch("polimex.hr.rfid.site.record_changed", {
        record_ids: [9999],
    });
    await waitForSteps(["load"]);
    expect(model.loadCount).toBe(1);
});

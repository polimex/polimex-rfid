/** @odoo-module **/

import {expect, test, beforeEach} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class HrRfidWebstack extends models.Model {
    _name = "hr.rfid.webstack";

    name = fields.Char();
    last_ip = fields.Char();

    _records = [
        {id: 1, name: "Webstack #1", last_ip: "192.168.1.50"},
        {id: 2, name: "Webstack #2", last_ip: "192.168.1.51"},
    ];

    _views = {
        list: /* xml */ `
            <list js_class="rfid_onboarding_list">
                <field name="name"/>
                <field name="last_ip"/>
            </list>
        `,
    };
}

beforeEach(() => {
    defineModels([HrRfidWebstack]);
});

test("rfid_onboarding_list renders banner above the list when steps exist", async () => {
    onRpc("onboarding.onboarding", "action_fetch_rfid_onboarding", () => ({
        closed: false,
        onboarding_state: "not_done",
        steps: [
            {
                id: 1,
                title: "Add a webstack",
                description: "Connect your first network controller",
                state: "not_done",
                button_text: "Setup",
                action: "action_open_setup",
            },
        ],
    }));

    await mountView({type: "list", resModel: "hr.rfid.webstack"});
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(1);
    expect(".o_onboarding_step_title").toHaveText("Add a webstack");
    expect(".o_list_view").toHaveCount(1);
});

test("rfid_onboarding_list hides banner when server returns closed=true", async () => {
    onRpc("onboarding.onboarding", "action_fetch_rfid_onboarding", () => ({
        closed: true,
    }));

    await mountView({type: "list", resModel: "hr.rfid.webstack"});
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(0);
    expect(".o_list_view").toHaveCount(1);
});

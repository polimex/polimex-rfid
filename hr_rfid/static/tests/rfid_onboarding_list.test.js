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
            <list js_class="onboarding_list">
                <field name="name"/>
                <field name="last_ip"/>
            </list>
        `,
    };
}

class OnboardingOnboarding extends models.Model {
    _name = "onboarding.onboarding";
}

beforeEach(() => {
    defineModels([HrRfidWebstack, OnboardingOnboarding]);
});

test("onboarding_list renders the banner above the list", async () => {
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () =>
        `<div class="o_onboarding_main">
            <div class="o_onboarding_steps d-flex">
                <div class="o_onboarding_step">
                    <h5 class="o_onboarding_step_title">Add a webstack</h5>
                </div>
            </div>
         </div>`
    );

    await mountView({
        type: "list",
        resModel: "hr.rfid.webstack",
        context: {onboarding_route_name: "hr_rfid_setup"},
    });
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(1);
    expect(".o_onboarding_step_title").toHaveText("Add a webstack");
    expect(".o_list_view").toHaveCount(1);
});

test("onboarding_list shows no banner when the server returns nothing", async () => {
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () => false);

    await mountView({
        type: "list",
        resModel: "hr.rfid.webstack",
        context: {onboarding_route_name: "hr_rfid_setup"},
    });
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(0);
    expect(".o_list_view").toHaveCount(1);
});

test("onboarding_list omits the banner when no route is configured", async () => {
    await mountView({type: "list", resModel: "hr.rfid.webstack"});
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(0);
    expect(".o_list_view").toHaveCount(1);
});

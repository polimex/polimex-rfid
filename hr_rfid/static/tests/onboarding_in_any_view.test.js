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
import {registry} from "@web/core/registry";
import {listView} from "@web/views/list/list_view";
import {ListController} from "@web/views/list/list_controller";

/**
 * The banner belongs to the action, not to a view class.
 *
 * It used to be a view class of its own, and a view carries exactly one
 * js_class - so the day a second module claimed one on the same view, the
 * banner vanished with no error anywhere. That is what happened on every
 * database carrying hr_rfid_refresh_views, which is auto-installed: it writes
 * js_class="list_refresh_view" over the User Events list and the banner was
 * simply never built. The last test here is the one that would have caught it.
 */

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
            <list>
                <field name="name"/>
                <field name="last_ip"/>
            </list>
        `,
        "list,2": /* xml */ `
            <list js_class="some_other_view_class">
                <field name="name"/>
                <field name="last_ip"/>
            </list>
        `,
    };
}

class OnboardingOnboarding extends models.Model {
    _name = "onboarding.onboarding";
}

const PANEL = `<div class="o_onboarding_main">
    <div class="o_onboarding_steps d-flex">
        <div class="o_onboarding_step">
            <h5 class="o_onboarding_step_title">Add a webstack</h5>
        </div>
    </div>
 </div>`;

beforeEach(() => {
    defineModels([HrRfidWebstack, OnboardingOnboarding]);
    // Stands in for any module that claims the view class for its own purpose -
    // hr_rfid_refresh_views does exactly this to keep the list up to date.
    registry.category("views").add(
        "some_other_view_class",
        {...listView, Controller: class extends ListController {}},
        {force: true},
    );
});

test("the banner is shown above the records when the action asks for it", async () => {
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () => PANEL);

    await mountView({
        type: "list",
        resModel: "hr.rfid.webstack",
        context: {onboarding_route_name: "hr_rfid_setup"},
    });
    await animationFrame();

    expect(".o_list_view .o_onboarding_main").toHaveCount(1);
    expect(".o_onboarding_step_title").toHaveText("Add a webstack");
});

test("no banner when the setup has already been put away", async () => {
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

test("no banner on a screen that never asked for one", async () => {
    let asked = false;
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () => {
        asked = true;
        return PANEL;
    });

    await mountView({type: "list", resModel: "hr.rfid.webstack"});
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(0);
    expect(".o_list_view").toHaveCount(1);
    expect(asked).toBe(false, {
        message: "a screen without onboarding must not even ask the server",
    });
});

test("another module claiming the view class does not take the banner away", async () => {
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () => PANEL);

    await mountView({
        type: "list",
        resModel: "hr.rfid.webstack",
        viewId: 2,
        context: {onboarding_route_name: "hr_rfid_setup"},
    });
    await animationFrame();

    expect(".o_list_view .o_onboarding_main").toHaveCount(1, {
        message: "the banner follows the action, so any view class may be used",
    });
});

/** @odoo-module **/

import {expect, test, beforeEach} from "@odoo/hoot";
import {click, queryAllTexts} from "@odoo/hoot-dom";
import {animationFrame} from "@odoo/hoot-mock";
import {
    asyncStep,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

class HrRfidSite extends models.Model {
    _name = "hr.rfid.site";

    name = fields.Char();
    parent_id = fields.Many2one({relation: "hr.rfid.site"});

    _records = [{id: 1, name: "Main Building", parent_id: false}];

    _views = {
        form: /* xml */ `
            <form>
                <field name="name"/>
                <widget name="site_chart"/>
            </form>
        `,
    };
}

beforeEach(() => {
    defineModels([HrRfidSite]);
});

test("site_chart widget loads and renders the hierarchy", async () => {
    onRpc("hr.rfid.site", "get_site_hierarchy", () => ({
        self: {id: 1, name: "Main Building", doors: 4},
        parent: false,
        children: [
            {id: 2, name: "Floor 1", doors: 2},
            {id: 3, name: "Floor 2", doors: 2},
        ],
    }));

    await mountView({type: "form", resModel: "hr.rfid.site", resId: 1});
    await animationFrame();

    expect(".o_site_chart").toHaveCount(1);
    expect(queryAllTexts(".site_name")).toEqual(["Main Building", "Floor 1", "Floor 2"]);
});

test("site_chart parent block appears when parent is set", async () => {
    onRpc("hr.rfid.site", "get_site_hierarchy", () => ({
        self: {id: 2, name: "Floor 1", doors: 2},
        parent: {id: 1, name: "Main Building", doors: 4},
        children: [],
    }));

    HrRfidSite._records = [{id: 2, name: "Floor 1", parent_id: 1}];

    await mountView({type: "form", resModel: "hr.rfid.site", resId: 2});
    await animationFrame();

    expect(".o_site_chart_parent").toHaveCount(1);
    expect(".o_site_chart_self").toHaveCount(1);
});

test("clicking site name dispatches a form-view action", async () => {
    onRpc("hr.rfid.site", "get_site_hierarchy", () => ({
        self: {id: 1, name: "Main Building", doors: 4},
        parent: false,
        children: [{id: 2, name: "Floor 1", doors: 2}],
    }));

    mockService("action", {
        async doAction(action) {
            asyncStep(`doAction:${action.res_model}:${action.res_id}`);
            return true;
        },
    });

    await mountView({type: "form", resModel: "hr.rfid.site", resId: 1});
    await animationFrame();

    await click(".o_site_chart_children .site_name a");
    await waitForSteps(["doAction:hr.rfid.site:2"]);
});

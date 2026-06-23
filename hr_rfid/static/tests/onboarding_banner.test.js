/** @odoo-module **/

import {expect, test, beforeEach} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {
    defineModels,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {OnboardingBanner} from "@hr_rfid/components/onboarding/onboarding";

class OnboardingOnboarding extends models.Model {
    _name = "onboarding.onboarding";
}

beforeEach(() => {
    defineModels([OnboardingOnboarding]);
});

test("banner stays empty when the server returns nothing", async () => {
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () => false);

    await mountWithCleanup(OnboardingBanner, {props: {routeName: "hr_rfid_setup"}});
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(0);
});

test("banner injects the server-rendered onboarding panel markup", async () => {
    // The component injects the core onboarding HTML verbatim; assert the
    // native onboarding markup (o_onboarding_main / step title) is present.
    onRpc("onboarding.onboarding", "get_onboarding_panel_html", () =>
        `<div class="o_onboarding_main">
            <div class="o_onboarding_steps d-flex">
                <div class="o_onboarding_step">
                    <h5 class="o_onboarding_step_title">Connect a webstack</h5>
                </div>
            </div>
         </div>`
    );

    await mountWithCleanup(OnboardingBanner, {props: {routeName: "hr_rfid_setup"}});
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(1);
    expect(".o_onboarding_step_title").toHaveText("Connect a webstack");
});

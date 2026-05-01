/** @odoo-module **/

import {expect, test, beforeEach} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {
    defineModels,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {RfidOnboardingBanner} from "@hr_rfid/components/onboarding/onboarding";

class OnboardingOnboarding extends models.Model {
    _name = "onboarding.onboarding";
}

class OnboardingOnboardingStep extends models.Model {
    _name = "onboarding.onboarding.step";
}

beforeEach(() => {
    defineModels([OnboardingOnboarding, OnboardingOnboardingStep]);
});

test("banner hides when server returns closed=true", async () => {
    onRpc("onboarding.onboarding", "action_fetch_rfid_onboarding", () => ({
        closed: true,
    }));

    await mountWithCleanup(RfidOnboardingBanner);
    await animationFrame();

    expect(".o_onboarding_main").toHaveCount(0);
});

test("banner renders steps returned by the server", async () => {
    onRpc("onboarding.onboarding", "action_fetch_rfid_onboarding", () => ({
        closed: false,
        onboarding_state: "not_done",
        steps: [
            {
                id: 1,
                title: "Connect a webstack",
                description: "Add your first network controller",
                state: "not_done",
                button_text: "Open settings",
                action: "action_open_step_1",
            },
        ],
    }));

    await mountWithCleanup(RfidOnboardingBanner);
    await animationFrame();

    expect(".o_onboarding_step").toHaveCount(1);
    expect(".o_onboarding_step_title").toHaveText("Connect a webstack");
});

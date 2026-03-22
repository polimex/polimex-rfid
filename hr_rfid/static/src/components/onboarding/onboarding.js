/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RfidOnboardingBanner extends Component {
    static template = "hr_rfid.OnboardingBanner";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            steps: [],
            onboardingState: "not_done",
            html: false,
        });
        onWillStart(() => this.loadOnboardingData());
        onWillUpdateProps(() => this.loadOnboardingData());
    }

    async loadOnboardingData() {
        const data = await this.orm.call(
            "onboarding.onboarding",
            "action_fetch_rfid_onboarding",
        );
        if (data && !data.closed) {
            this.state.steps = data.steps || [];
            this.state.onboardingState = data.onboarding_state || "not_done";
            this.state.html = true;
        } else {
            this.state.html = false;
        }
    }

    async onStepClicked(step) {
        const action = await this.orm.call(
            "onboarding.onboarding.step",
            step.action,
        );
        if (action) {
            await this.action.doAction(action, {
                onClose: () => this.loadOnboardingData(),
            });
        }
    }

    async onExtraActionClicked(step) {
        if (!step.extra_action) return;
        const action = await this.orm.call(
            "onboarding.onboarding.step",
            step.extra_action.method,
        );
        if (action) {
            await this.action.doAction(action, {
                onClose: () => this.loadOnboardingData(),
            });
        }
    }

    async onCloseBanner() {
        await this.orm.call(
            "onboarding.onboarding",
            "action_close_panel",
            ["hr_rfid.onboarding_rfid_setup"],
        );
        this.state.html = false;
    }
}

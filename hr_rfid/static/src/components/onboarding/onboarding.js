/** @odoo-module **/

import { Component, markup, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useActionLinks } from "@web/views/view_hook";

/**
 * In-app onboarding banner.
 *
 * Instead of re-implementing Odoo's onboarding markup by hand, this banner
 * injects the server-rendered `onboarding.onboarding_panel` template and
 * delegates the step `type="action"` links to core's `useActionLinks` hook.
 * The result is identical to Odoo's native onboarding: same SCSS (so longer
 * translations stay inside the scrollable wrap), same step images, automatic
 * translation of every label.
 *
 * The close control is handled with Odoo's native OWL ConfirmationDialog
 * (not the core template's Bootstrap modal, whose JS is not reliably wired
 * in the OWL backend) so the banner is removed deterministically.
 *
 * `env.keepLast` (required by useActionLinks) is provided by the host View.
 */
export class OnboardingBanner extends Component {
    static template = "hr_rfid.OnboardingBanner";
    static props = {
        routeName: String,
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({ html: false });
        this.handleActionLinks = useActionLinks({
            resModel: "onboarding.onboarding",
            // Re-fetch after a step action closes so completion (and the
            // "just done" confetti / final close) is reflected immediately.
            reload: () => this.load(),
        });
        onWillStart(() => this.load());
        onWillUpdateProps(() => this.load());
    }

    async load() {
        const html = await this.orm.call(
            "onboarding.onboarding",
            "get_onboarding_panel_html",
            [this.props.routeName],
        );
        // The HTML comes from a trusted core QWeb template rendered with our
        // own onboarding records (titles/descriptions are escaped server-side
        // by t-out), so wrapping it as markup is safe.
        this.state.html = html ? markup(html) : false;
    }

    onPanelClick(ev) {
        // The close "X" opens a Bootstrap confirmation modal in the core
        // template; intercept it and use Odoo's native OWL ConfirmationDialog
        // instead, so we control the banner removal directly.
        if (ev.target.closest(".o_onboarding_btn_close")) {
            ev.preventDefault();
            ev.stopPropagation();
            this.confirmClose();
            return;
        }
        // Step buttons: let core open their action; reload happens via the
        // useActionLinks `reload` callback when the action dialog closes.
        this.handleActionLinks(ev);
    }

    confirmClose() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Hide onboarding tips"),
            body: _t("Are you sure you want to hide these configuration steps?"),
            confirmLabel: _t("Hide"),
            confirmClass: "btn-primary",
            confirm: async () => {
                // Persist the close by route, then drop the banner.
                await this.orm.call(
                    "onboarding.onboarding",
                    "close_onboarding_panel",
                    [this.props.routeName],
                );
                this.state.html = false;
            },
            cancel: () => {},
        });
    }
}

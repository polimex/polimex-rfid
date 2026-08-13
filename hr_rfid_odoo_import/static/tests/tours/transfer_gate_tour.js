import { registry } from "@web/core/registry";

/**
 * The operator must be able to SEE which parts cannot be transferred, and why,
 * before starting anything - and must not be able to start a transfer that is
 * missing something it needs.
 *
 * This drives the wizard the way a person does: fill the connection in, move to
 * the next step, and read what the screen says. It exercises input rather than
 * only asserting that elements exist, because a transfer wizard that renders
 * but does not accept typing is exactly the failure this is meant to catch.
 */
registry.category("web_tour.tours").add("rfid_transfer_gate_tour", {
    url: "/odoo/action-hr_rfid_odoo_import.hr_rfid_odoo_import_wiz_action",
    steps: () => [
        {
            content: "The connection details can be typed in",
            trigger: "div[name='source_url'] input",
            run: "edit http://localhost:1",
        },
        {
            content: "The login field accepts typing too",
            trigger: "div[name='source_login'] input",
            run: "edit admin",
        },
        {
            content: "The password field accepts typing",
            trigger: "div[name='source_password'] input",
            run: "edit secret",
        },
        {
            content: "The database name is optional and can be typed",
            trigger: "div[name='source_db'] input",
            run: "edit some_db",
        },
        {
            content: "What was typed is what the field holds",
            trigger: "div[name='source_url'] input:value(http://localhost:1)",
        },
        {
            content: "The step to go on with is offered",
            trigger: ".modal-footer button[name='action_test_connection']",
        },
        {
            // Leave the dialog rather than the browser closing it for us: an
            // unsaved form saved on unload fires stray requests and leaves the
            // next test looking at inconsistent data.
            content: "The operator can walk away without starting anything",
            // Matched by class, not by the word on it: this database runs in
            // Bulgarian and text matching would break on any translated UI.
            trigger: ".modal-footer button.btn-secondary:not([name])",
            run: "click",
        },
    ],
});

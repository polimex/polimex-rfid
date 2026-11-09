import { registry } from "@web/core/registry";

/**
 * E2E tours - the controller form shows what each vending firmware can use.
 *
 * Process: a technician opens the controller a vending machine reported.
 * Every vending machine has the vending page instead of the IO table editor.
 * A machine that sells at the prices entered in Odoo (16, 20) also has the
 * Prices button; an MDB machine (21) keeps its own prices and has none.
 *
 * The form renders its smart buttons in `.o-form-buttonbox`; the ones that do
 * not fit go into the "More" dropdown, which renders in an overlay with the
 * same class. Every tour opens "More" first and then looks in both places, so
 * an absent button is absent from the whole box, not only from the first row.
 * Buttons and pages are found by the ids and page names of the view, never by
 * their labels: the screen is in the user's language.
 *
 * The HttpCase opens the form of the controller it built; the url carries
 * the record id.
 */
const formRendered = {
    content: "The controller form rendered",
    trigger: ".o_form_view .o_form_sheet",
};
const openMoreButtons = {
    content: "Open the smart buttons that did not fit, if any",
    trigger: ".o_form_view .o-form-buttonbox",
    run: () => {
        document.querySelector(".o_form_view .o_button_more")?.click();
    },
};
const allButtonsShown = {
    content: "Every smart button is on the screen",
    trigger: ".o_dropdown_more, .o_form_view .o-form-buttonbox:not(:has(.o_button_more))",
};
const vendingPage = {
    content: "The vending page is offered",
    trigger: ".o_notebook_headers a[name='vending']",
};
const noIoTableEditor = {
    content: "The IO table editor is not offered on a vending machine",
    trigger: "body:not(:has(button#hr_rfid_view_modify_io_table_btn))",
};

registry.category("web_tour.tours").add("hr_rfid_vending_price_table_form_tour", {
    steps: () => [
        formRendered,
        openMoreButtons,
        allButtonsShown,
        {
            content: "The Prices button is there, with its table icon",
            trigger: "button#hr_rfid_vending_settings_btn.oe_stat_button:has(i.fa-table)",
        },
        noIoTableEditor,
        vendingPage,
    ],
});

registry.category("web_tour.tours").add("hr_rfid_vending_door_controller_form_tour", {
    steps: () => [
        formRendered,
        openMoreButtons,
        allButtonsShown,
        {
            content: "A door controller keeps its IO table editor",
            trigger: "button#hr_rfid_view_modify_io_table_btn.oe_stat_button:has(i.fa-table)",
        },
        {
            content: "No Prices button on a door controller",
            trigger: "body:not(:has(button#hr_rfid_vending_settings_btn))",
        },
        {
            content: "No vending page on a door controller",
            trigger: ".o_notebook_headers:not(:has(a[name='vending']))",
        },
    ],
});

registry.category("web_tour.tours").add("hr_rfid_vending_own_prices_form_tour", {
    steps: () => [
        formRendered,
        openMoreButtons,
        allButtonsShown,
        {
            content: "No Prices button: the machine keeps its own prices",
            trigger: "body:not(:has(button#hr_rfid_vending_settings_btn))",
        },
        noIoTableEditor,
        vendingPage,
    ],
});

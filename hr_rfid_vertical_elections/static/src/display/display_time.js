/** @odoo-module **/

import { useInterval } from "@hr_rfid_vertical_elections/display/useInterval";

import { Component, useState, xml } from "@odoo/owl";

export class DisplayTime extends Component {
    static template = xml`<div class="d-flex flex-column justify-content-center"><span class="display-6" t-out="state.currentTime.toFormat('T')"/><span class="smaller" t-out="state.currentTime.toFormat('DDDD')"/></div>`;

    setup() {
        this.state = useState({ currentTime: luxon.DateTime.now() });
        // Update the current time every second
        useInterval(() => (this.state.currentTime = luxon.DateTime.now()), 1000);
    }
}

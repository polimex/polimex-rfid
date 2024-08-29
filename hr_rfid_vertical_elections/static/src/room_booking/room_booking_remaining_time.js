/** @odoo-module **/

import { useInterval } from "@room/room_booking/useInterval";

import { Component, useState, xml } from "@odoo/owl";

export class RoomBookingRemainingTime extends Component {
    static template = xml`
        <div class="o_room_remaining_time mt-5 w-100 rounded py-3 bg-black-25 display-4 text-center text-white"
             t-out="state.remainingTime.toFormat('hh:mm:ss')"/>
    `;
    static props = {
        endTime: { type: Object },
    };

    setup() {
        this.state = useState({ remainingTime: this.props.endTime.diffNow() });
        // Update the remaining time every second
        useInterval(() => (this.state.remainingTime = this.props.endTime.diffNow()), 1000);
    }
}

/** @odoo-module **/

import {useInterval} from "@hr_rfid_vertical_elections/display/useInterval";
import {deserializeDateTime, serializeDateTime} from "@web/core/l10n/dates";

import {Component, EventBus, useState, xml} from "@odoo/owl";

export class SessionRemainingTime extends Component {
    static template = xml`
        <div class="o_display_remaining_time mt-5 w-100 rounded py-3 bg-black-25 display-4 text-center text-white">
             <span t-out="state.timePast.toFormat('hh:mm:ss')"/>
             <div class="progress w-100 mt-2" style="height: 1px;">
                <div class="progress-bar" role="progressbar" 
                     t-att-style="'width: ' + (state.timePast.as('seconds') / props.currentSession.voting_time * 100) + '%;'" 
                     t-att-aria-valuenow="state.timePast.as('seconds')" 
                     t-att-aria-valuemin="0" 
                     t-att-aria-valuemax="props.currentSession.voting_time">
                </div>
            </div>
        </div>     
             
    `;
    static props = {
        currentSession: {type: Object},
        onVotingEnd: {type: Function},
    };

    setup() {
        if (this.props.currentSession.start_datetime) {
            this.startTime = deserializeDateTime(this.props.currentSession.start_datetime);
            this.state = useState({
                votingEnd: false,
                timePast: luxon.DateTime.now().diff(this.startTime),
            });

            useInterval(this.intervalAction.bind(this), 1000);
        }
    }

    intervalAction() {
        const currentTime = luxon.DateTime.now();
        this.state.timePast = currentTime.diff(this.startTime);
        console.log('seconds', this.state.timePast.as("seconds"), 'voting_time', this.props.currentSession.voting_time);
        if (this.state.timePast.as("seconds") > this.props.currentSession.voting_time) {
            console.log('Voting time is over');
            this.props.onVotingEnd(this.props.currentSession.id);
        }
    }
}
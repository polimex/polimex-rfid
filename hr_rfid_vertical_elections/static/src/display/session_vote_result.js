/** @odoo-module **/

import {useInterval} from "@hr_rfid_vertical_elections/display/useInterval";
import {deserializeDateTime, serializeDateTime} from "@web/core/l10n/dates";

import {Component, useState, xml} from "@odoo/owl";

export class SessionVoteResult extends Component {
    static template = xml`
        <div class="o_display_remaining_time mt-5 w-100 rounded py-3 bg-black-25 display-4 text-center text-white">
            <t t-if="props.currentSession.final_vote === 'no_vote'">
                <span class="text-uppercase">No votes</span>
            </t>
            <t t-else="">
                <span t-out="props.currentSession.final_vote" class="text-uppercase"/>
            </t>
            <div class="progress w-100 mt-2" style="height: 1px;">
                <div class="progress-bar" role="progressbar" 
                     t-att-style="'width: ' + (state.currentTime / vote_results_time * 100) + '%;'" 
                     t-att-aria-valuenow="state.currentTime" 
                     t-att-aria-valuemin="0" 
                     t-att-aria-valuemax="vote_results_time">
                </div>
            </div>
        </div>
    `;
    static props = {
        currentSession: {type: Object},
        onVoteResultEnd: {type: Function},
    };

    setup() {
        if (this.props.currentSession.start_datetime) {
            if (this.props.currentSession.final_vote === 'no_vote')
                this.vote_results_time = 10;
             else
                this.vote_results_time = this.props.currentSession.vote_results_time;
            console.log('vote_results_time', this.vote_results_time);
            // this.startTime = deserializeDateTime(this.props.startTime);
            // const endTime = this.startTime.plus({seconds: this.props.voting_time});
            this.state = useState({
                 currentTime: 0,
                // timePast: luxon.DateTime.now().diff(this.startTime),
                // timeToEnd: endTime.diff(luxon.DateTime.now())
            });

            // Define intervalAction within the setup method
            const intervalAction = () => {
                this.state.currentTime += 1;
                if (this.state.currentTime > this.vote_results_time) {
                    console.log('Voting results time is over');
                    this.props.onVoteResultEnd(this.props.currentSession.id);
                }
            };

            // Use intervalAction in useInterval
            useInterval(intervalAction, 1000);
        }
    }
}

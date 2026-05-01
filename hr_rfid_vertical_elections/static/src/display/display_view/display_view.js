/** @odoo-module **/

import {deserializeDateTime} from "@web/core/l10n/dates";
import {redirect} from "@web/core/utils/urls";
import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";
import {SessionRemainingTime} from "@hr_rfid_vertical_elections/display/session_remaining_time";
import {SessionVoteResult} from "@hr_rfid_vertical_elections/display/session_vote_result";
import {DisplayTime} from "@hr_rfid_vertical_elections/display/display_time";
import {useInterval} from "@hr_rfid_vertical_elections/display/useInterval";
import {useService} from "@web/core/utils/hooks";

import {Component, onWillStart, useState} from "@odoo/owl";

export class DisplayView extends Component {
    static components = {
        SessionRemainingTime,
        SessionVoteResult,
        DisplayTime,
    };
    static template = "hr_rfid_vertical_elections.DisplayView";

    setup() {
        this.manageDisplayUrl = `/voting_display/${this.props.accessToken}`;

        this.state = useState({
            sessions: [],
            currentSession: null,
            currentSessionVoteEnded: false,
            currentDate: this.now.startOf("day"),
        });
        // Show sessions updates in live
        this.busService = this.env.services.bus_service;
        const msg_prefix = 'display';
        this.busService.addChannel(msg_prefix + "#" + this.props.accessToken);
        this.busService.subscribe("session/change_state", (sessions) =>
            sessions.forEach((session) => this.updateSessionState(session)),
        );
        this.busService.subscribe("session/voting", (sessions) =>
            sessions.forEach((session) => this.updateSessionVoting(session)),
        );
        this.busService.subscribe("reload", (url) => redirect(url));

        this.notification = useService("notification");
        onWillStart(this.loadSessions);

        // Every second, check if a session started/ended
        useInterval(this.refreshDisplayView.bind(this), 1000);
    }

    async closeSession(sessionId) {
        try {
            await rpc(`${this.manageDisplayUrl}/session/${sessionId}/close`, {
                state: "closed",
            });
        } catch (error) {
            this.notification.add(
                error.data?.message || error.message || "Failed to close session",
                {type: "danger"},
            );
        }
    }

    //----------------------------------------------------------------------
    // Formats
    //----------------------------------------------------------------------

    get timeFormat() {
        return luxon.DateTime.TIME_SIMPLE;
    }

    get dateFormat() {
        return luxon.DateTime.DATE_HUGE;
    }

    //----------------------------------------------------------------------
    // Getters
    //----------------------------------------------------------------------

    /**
     * Return the background color of the main view which depends on the
     * room's availability
     */
    get bgColor() {
        return (
            (this.state.currentSession && !this.state.currentSessionVoteEnded ? this.props.votingBgColor : this.props.noVotingBgColor) +
            "DD"
        );
    }

    get now() {
        return luxon.DateTime.now();
    }

    //----------------------------------------------------------------------
    // Methods
    //----------------------------------------------------------------------

    onVotingEnd(sessionId) {
        if (this.state.currentSession.id === sessionId) {
            this.state.currentSessionVoteEnded = true;
            this.render();
        }
    }

    onVoteResultEnd() {
        this.closeSession(this.state.currentSession.id);
        this.state.currentSessionVoteEnded = false;
        this.state.currentSession = null;
    }

    /**
     * Load the existing sessions for the display.
     */
    async loadSessions() {
        const sessions = await rpc(`${this.manageDisplayUrl}/get_existing_sessions`);
        // Reorder the sessions by state. First the open sessions, then draft ones then the closed ones
        sessions.sort((a, b) => {
            const states = ["open", "draft", "closed"];
            return states.indexOf(a.state) - states.indexOf(b.state);
        });
        for (const session of sessions) {
            this.addSession(session);
        }
        this.refreshDisplayView();
    }

    /**
     * Update the current status of the room (booked or available), and remove
     * the booking of the list of bookings if it is finished.
     */
    refreshDisplayView() {
        if (this.state.sessions.length > 0) {
            // find the session that is open for voting
            const currentSession = this.state.sessions.find(
                (session) => session.state === "open"
            );
            // this.state.currentSessionVoteEnded = false;
            if (currentSession) {
                this.state.currentSession = currentSession;
                // this.state.currentSessionVoteEnded = false;
            } else {
                this.state.currentSession = null;
            }
        }

    }


    //----------------------------------------------------------------------
    // Bus Methods
    //----------------------------------------------------------------------

    addSession(newSession) {
        newSession.interval = luxon.Interval.fromDateTimes(
            deserializeDateTime(newSession.start_datetime),
            deserializeDateTime(newSession.end_datetime),
        );
        const newSessionInsertIdx = this.state.sessions.findIndex(
            (session) => session.interval.start > newSession.interval.start,
        );
        if (newSessionInsertIdx === -1) {
            this.state.sessions.push(newSession);

        } else {
            this.state.sessions.splice(newSessionInsertIdx, 0, newSession);
        }
    }


    updateSessionState(session) {
        const sessionIdx = this.state.sessions.findIndex((s) => s.id === session.id);
        if (sessionIdx === -1) {
            return;
        }
        this.state.sessions[sessionIdx] = session;
        this.state.sessions.sort((a, b) => {
            const states = ["open", "draft", "closed"];
            return states.indexOf(a.state) - states.indexOf(b.state);
        });
    }

    /**
     * Update the given session with the new values. For simplicity, the existing session
     * @param updSession
     */
    updateSessionVoting(updSession) {
        const sessionIdx = this.state.sessions.findIndex((session) => session.id === updSession.id);
        if (sessionIdx !== -1 && this.state.sessions[sessionIdx].state === "open") {
            this.state.sessions[sessionIdx].vote_abstain = updSession.vote_abstain;
            this.state.sessions[sessionIdx].vote_no = updSession.vote_no;
            this.state.sessions[sessionIdx].vote_yes = updSession.vote_yes;
            this.state.sessions[sessionIdx].vote_total = updSession.vote_total;
            this.state.sessions[sessionIdx].final_vote = updSession.final_vote;
        }
    }
}

registry.category("public_components").add("hr_rfid_vertical_elections.display_view", DisplayView);

/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {deserializeDateTime, serializeDateTime} from "@web/core/l10n/dates";
import {redirect} from "@web/core/utils/urls";
import {registry} from "@web/core/registry";
import {SessionRemainingTime} from "@hr_rfid_vertical_elections/display/session_remaining_time";
import {SessionVoteResult} from "@hr_rfid_vertical_elections/display/session_vote_result";
import {DisplayTime} from "@hr_rfid_vertical_elections/display/display_time";
import {useInterval} from "@hr_rfid_vertical_elections/display/useInterval";
import { useService} from "@web/core/utils/hooks";
import { makeEnv, startServices } from "@web/env";
import { templates } from "@web/core/assets";
import { busService } from "@bus/services/bus_service";

import {
    Component,
    markup,
    onWillStart,
    onWillUnmount,
    useExternalListener,
    useState,
    EventBus, xml, whenReady, App
} from "@odoo/owl";

// Time (in ms, so 2 minutes) after which the user is considered inactive
// and the app goes back to the main screen
const INACTIVITY_TIMEOUT = 120000;

export class DisplayViewApp extends Component {
    static components = {
        SessionRemainingTime,
        SessionVoteResult,
        DisplayTime,
    };

    setup() {
        this.manageDisplayUrl = `/voting_display/${this.props.accessToken}`;
        this.lang = this.props.lang;
        this.msg_discuss = _t("Discussions");
        // const bus = new EventBus();
        // bus.addEventListener('voting-end', this.onVotingEnd.bind(this));
        this.state = useState({
            sessions: [],
            currentSession: null,
            currentSessionVoteEnded: false,
            currentDate: this.now.startOf("day"),
        });
        // Show sessions updates in live
        this.busService = this.env.services.bus_service;
        // this.busService = useService("bus_service");
        const msg_prefix = 'display'
        this.busService.addChannel(msg_prefix + "#" + this.props.accessToken);
        this.busService.subscribe("session/change_state", (sessions) =>
            sessions.forEach((session) => this.udpateSessionState(session)),
        );
        this.busService.subscribe("session/voting", (sessions) =>
            sessions.forEach((session) => this.udpateSessionVoting(session)),
        );
        this.busService.subscribe("reload", (url) => redirect(url));

        this.rpc = useService("rpc");
        this.notificationService = useService("notification");
        this.dialogService = useService("dialog");
        onWillStart(this.loadSessions);

        // Every second, check if a booking started/ended
        useInterval(this.refreshDisplayView.bind(this), 1000);

        // If the user is inactive for more than the  INACTIVITY_TIMEOUT, reset the view
        // ["pointderdown", "keydown"].forEach((event) =>
        //     useExternalListener(window, event, () => {
        //         clearTimeout(this.inactivityTimer);
        //         this.inactivityTimer = setTimeout(() => {
        //             this.resetBookingForm();
        //         }, INACTIVITY_TIMEOUT);
        //     }),
        // );
        onWillUnmount(() => clearTimeout(this.inactivityTimer));

        // this.onVotingEnd = this.onVotingEnd.bind(this);
    }

    closeSession(sessionId) {
        this.rpc(`${this.manageDisplayUrl}/session/${sessionId}/close`, {
            state : 'closed',
            // start_datetime: serializeDateTime(start),
            // stop_datetime: serializeDateTime(end),
        });
        // this.resetBookingForm();
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

    /**
     * @returns {string} Raw HTML of the description
     */
    get displayDescription() {
        return markup(this.props.description);
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
        console.log("Voting results have ended.");
        this.closeSession(this.state.currentSession.id);
        this.state.currentSessionVoteEnded = false;
        this.state.currentSession = null;
        // Add any additional logic to handle the end of voting results
    }

    /**
     * Load the existing sessions for the display.
     */
    async loadSessions() {
        const sessions = await this.rpc(`${this.manageDisplayUrl}/get_existing_sessions`);
        // Reorder the sessions by state. First the open sessions, then draft ones then the closed ones
        sessions.sort((a, b) => {
            const states = ["open", "draft", "closed"];
            return states.indexOf(a.state) - states.indexOf(b.state);
        });
        console.log('sessions', sessions);
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


    udpateSessionState(sesssion) {
        console.log('udpateSessionState', sesssion);
        // Find the sessoion to udpate
        const sessionIdx = this.state.sessions.findIndex((session) => session.id === sesssion.id);
        // Update the session
        this.state.sessions[sessionIdx] = sesssion;
        this.state.sessions.sort((a, b) => {
            const states = ["open", "draft", "closed"];
            return states.indexOf(a.state) - states.indexOf(b.state);
        });

        // this.removeBooking(sesssion.id);
        // this.addBooking(sesssion);
    }

    /**
     * Update the given session with the new values. For simplicity, the existing session
     * @param updSesssion
     */
    udpateSessionVoting(updSesssion) {
        console.log('udpateSessionVoting', updSesssion);
        // Find the session to update
        const sessionIdx = this.state.sessions.findIndex((session) => session.id === updSesssion.id);
        // Update the session votes
        //check if session
        if (sessionIdx !== -1 && this.state.sessions[sessionIdx].state === "open") {
            this.state.sessions[sessionIdx].vote_abstain = updSesssion.vote_abstain;
            this.state.sessions[sessionIdx].vote_no = updSesssion.vote_no;
            this.state.sessions[sessionIdx].vote_yes = updSesssion.vote_yes;
            this.state.sessions[sessionIdx].vote_total = updSesssion.vote_total;
            this.state.sessions[sessionIdx].final_vote = updSesssion.final_vote;
        }
    }
}

DisplayViewApp.template = "hr_rfid_vertical_elections.display_main_view";

export async function createPublicDisplay(document, display_info) {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    const app = new App(DisplayViewApp, {
        templates,
        env: env,
        props:
            {
                id: display_info.id,
                description: display_info.description,
                name: display_info.name,
                company_name: display_info.company_name,
                accessToken: display_info.access_token,
                noVotingBgColor: display_info.no_voting_background_color,
                votingBgColor: display_info.voting_background_color,
                lang: display_info.lang,
            },
        dev: env.debug,
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    return app.mount(document.body);
}

export default { DisplayViewApp, createPublicDisplay };

// registry.category("public_components").add("hr_rfid_vertical_elections.display_view", DisplayView);

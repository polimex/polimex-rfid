/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {advanceTime} from "@odoo/hoot-dom";
import {animationFrame} from "@odoo/hoot-mock";
import {mountWithCleanup} from "@web/../tests/web_test_helpers";
import {SessionVoteResult} from "@hr_rfid_vertical_elections/display/session_vote_result";

const luxon = window.luxon;

const baseSession = {
    id: 1,
    start_datetime: luxon.DateTime.now().toISO(),
    voting_time: 300,
    vote_results_time: 5,
    final_vote: "yes",
};

test("SessionVoteResult shows the final vote uppercase", async () => {
    await mountWithCleanup(SessionVoteResult, {
        props: {
            currentSession: {...baseSession, final_vote: "yes"},
            onVoteResultEnd: () => {},
        },
    });
    await animationFrame();

    expect(".text-uppercase").toHaveText("yes");
});

test("SessionVoteResult shows 'No votes' when final_vote === 'no_vote'", async () => {
    await mountWithCleanup(SessionVoteResult, {
        props: {
            currentSession: {...baseSession, final_vote: "no_vote"},
            onVoteResultEnd: () => {},
        },
    });
    await animationFrame();

    expect(".o_display_remaining_time").toHaveText(/No votes/);
});

test("SessionVoteResult fires onVoteResultEnd after vote_results_time", async () => {
    let endedSessionId = null;
    await mountWithCleanup(SessionVoteResult, {
        props: {
            currentSession: {...baseSession, id: 7, vote_results_time: 2},
            onVoteResultEnd: (id) => {
                endedSessionId = id;
            },
        },
    });
    await animationFrame();

    await advanceTime(3500);
    await animationFrame();

    expect(endedSessionId).toBe(7);
});

test("SessionVoteResult uses 10s fallback for no_vote sessions", async () => {
    let endedSessionId = null;
    await mountWithCleanup(SessionVoteResult, {
        props: {
            currentSession: {
                ...baseSession,
                id: 8,
                final_vote: "no_vote",
                vote_results_time: 1,
            },
            onVoteResultEnd: (id) => {
                endedSessionId = id;
            },
        },
    });
    await animationFrame();

    // After 2s — vote_results_time (1) would have fired, but no_vote fallback (10s) should still hold.
    await advanceTime(2500);
    await animationFrame();
    expect(endedSessionId).toBe(null);

    // After ~11s total it should fire.
    await advanceTime(9000);
    await animationFrame();
    expect(endedSessionId).toBe(8);
});

/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {advanceTime} from "@odoo/hoot-dom";
import {animationFrame} from "@odoo/hoot-mock";
import {mountWithCleanup} from "@web/../tests/web_test_helpers";
import {SessionRemainingTime} from "@hr_rfid_vertical_elections/display/session_remaining_time";

const luxon = window.luxon;

test("SessionRemainingTime renders progress bar", async () => {
    const startedAt = luxon.DateTime.now().minus({seconds: 30}).toISO();
    await mountWithCleanup(SessionRemainingTime, {
        props: {
            currentSession: {
                id: 1,
                start_datetime: startedAt,
                voting_time: 300,
            },
            onVotingEnd: () => {},
        },
    });
    await animationFrame();

    expect(".o_display_remaining_time").toHaveCount(1);
    expect(".progress-bar").toHaveCount(1);
});

test("SessionRemainingTime fires onVotingEnd when voting_time is exceeded", async () => {
    const startedAt = luxon.DateTime.now().minus({seconds: 9}).toISO();
    let endedSessionId = null;

    await mountWithCleanup(SessionRemainingTime, {
        props: {
            currentSession: {
                id: 42,
                start_datetime: startedAt,
                voting_time: 10,
            },
            onVotingEnd: (id) => {
                endedSessionId = id;
            },
        },
    });
    await animationFrame();

    // After two seconds the cumulative diff (~11s) exceeds voting_time (10s).
    await advanceTime(2000);
    await animationFrame();

    expect(endedSessionId).toBe(42);
});

test("SessionRemainingTime without start_datetime is a no-op", async () => {
    await mountWithCleanup(SessionRemainingTime, {
        props: {
            currentSession: {id: 1, start_datetime: false, voting_time: 60},
            onVotingEnd: () => {
                throw new Error("should not fire");
            },
        },
    });
    await animationFrame();
    await advanceTime(2000);
    await animationFrame();
    // No throw means the test passed; the component must skip its setup body.
    expect(true).toBe(true);
});

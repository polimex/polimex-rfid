/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {mockService, mountWithCleanup, onRpc} from "@web/../tests/web_test_helpers";
import {DisplayView} from "@hr_rfid_vertical_elections/display/display_view/display_view";

const baseProps = {
    accessToken: "test-token",
    name: "Test Display",
    company_name: "Polimex",
    description: "",
    votingBgColor: "#ff0000",
    noVotingBgColor: "#00ff00",
};

function mockBusService() {
    mockService("bus_service", {
        addChannel() {},
        deleteChannel() {},
        subscribe() {},
        unsubscribe() {},
    });
}

test("renders idle state when no sessions are open", async () => {
    mockBusService();
    onRpc("/voting_display/test-token/get_existing_sessions", () => []);

    await mountWithCleanup(DisplayView, {props: baseProps});
    await animationFrame();

    expect(".o_display_main").toHaveCount(1);
    expect(".o_display_main h1").toHaveText("Discussions");
});

test("renders open voting session with vote counters", async () => {
    mockBusService();
    onRpc("/voting_display/test-token/get_existing_sessions", () => [
        {
            id: 7,
            name: "Budget approval",
            state: "open",
            start_datetime: "2026-04-30 10:00:00",
            end_datetime: "2026-04-30 10:05:00",
            voting_time: 300,
            vote_results_time: 30,
            vote_yes: 4,
            vote_no: 1,
            vote_abstain: 2,
            vote_total: 7,
            final_vote: false,
        },
    ]);

    await mountWithCleanup(DisplayView, {props: baseProps});
    await animationFrame();

    expect(".o_display_main").toHaveText(/Budget approval/);
    expect(".o_display_main").toHaveText(/Yes:/);
    expect(".o_display_main").toHaveText(/Total votes:/);
});

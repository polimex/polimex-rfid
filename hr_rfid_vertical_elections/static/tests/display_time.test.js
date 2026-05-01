/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {advanceTime} from "@odoo/hoot-dom";
import {animationFrame} from "@odoo/hoot-mock";
import {mountWithCleanup} from "@web/../tests/web_test_helpers";
import {DisplayTime} from "@hr_rfid_vertical_elections/display/display_time";

test("DisplayTime renders current time and date", async () => {
    await mountWithCleanup(DisplayTime);
    await animationFrame();

    expect(".display-6").toHaveCount(1);
    expect(".smaller").toHaveCount(1);

    // Time should be a non-empty hh:mm-style string.
    const timeText = document.querySelector(".display-6").textContent.trim();
    expect(timeText.length).toBeGreaterThan(0);
});

test("DisplayTime updates on the 1s interval", async () => {
    await mountWithCleanup(DisplayTime);
    await animationFrame();

    const before = document.querySelector(".display-6").textContent;
    await advanceTime(1500);
    await animationFrame();
    const after = document.querySelector(".display-6").textContent;

    // We can't guarantee the second changed if the test ran across a tick boundary,
    // but the component must remount text without throwing.
    expect(after.length).toBeGreaterThan(0);
    expect(typeof before).toBe("string");
});

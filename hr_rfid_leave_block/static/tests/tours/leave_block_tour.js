import { registry } from "@web/core/registry";

/**
 * E2E tour — approving a leave suspends the employee's RFID cards.
 *
 * Process: a Time Off officer opens an employee's pending leave, which is
 * already going on, and clicks Approve. The employee's active RFID cards are
 * suspended at once (a leave that begins later stops them when it begins) and
 * an audit snapshot (hr.rfid.leave.block) is recorded. The tour drives the
 * approval; the Python driver asserts the card was deactivated and the block
 * was created.
 *
 * Pre-conditions (HttpCase fixture):
 *   * employee "LeaveBlock Tester" with one active hr.rfid.card
 *   * a leave for that employee in the 'confirm' (To Approve) state, opened
 *     directly via the tour URL (.../<leave_id>).
 */
registry.category("web_tour.tours").add("hr_rfid_leave_block_approve_tour", {
    steps: () => [
        {
            content: "Leave form loaded with an Approve action",
            trigger: ".o_form_view button[name='action_approve']",
        },
        {
            content: "Approve the leave",
            trigger: ".o_form_view button[name='action_approve']",
            run: "click",
        },
        {
            content: "Approved — a Refuse action is now offered (post-approval state)",
            trigger: ".o_form_view button[name='action_refuse']",
        },
    ],
});

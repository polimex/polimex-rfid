"""What a module is told when it reports - from the request to the reply.

A module reports three things: that it is alive (heartbeat), that something
happened at a door (event) and what a controller said to a command (response).
Each report is answered, and the answer is the only way anything reaches the
hardware of a site behind NAT: the next command, or nothing.

What the people who run a site need from that conversation:

* the module gets its answer in the language it speaks - an old 10.3 module
  reads a command or an empty reply and nothing else, a 100.1 reads plain JSON,
  a module that wraps its reports in JSON-RPC gets the answer wrapped the same;
* a change of somebody's access reaches the controller, and the next one
  follows it;
* one command that nobody answers does not hold up everything behind it, and
  the operator is told that it was not carried out;
* an answer that belongs to a moment - "may this card pass" - is never sent
  later;
* a report the system has no use for is kept and accepted, never answered with
  an error the module would keep repeating;
* a passage that arrives late does not undo what a newer one already settled;
* when something fails here, the report survives and says where.

Every test posts to the endpoint the hardware posts to and reads the reply the
hardware would read. Until now each test of that endpoint went through one
shape of reply only (10.3), and in that shape a crash looks exactly like
"nothing to do" - an empty reply - so a test that looked at the reply could not
tell them apart. The helper below fails any report that left a traceback
behind, unless the test is about the failure.
"""

import json
from datetime import timedelta
from unittest.mock import patch

from lxml import etree

from odoo import fields
from odoo.tests.common import HttpCase, tagged
from odoo.tools.safe_eval import safe_eval

from ..controllers.polimex import CMD_ANSWER_TIMEOUT_S, CMD_MAX_RETRIES
from .hardware import one_door

NO_CARD = "0000000000"
GRANTED_AT_READER = {1: 3, 2: 7}


class Reply:
    """What came back, as the module sees it."""

    def __init__(self, response, json_rpc):
        self.http_status = response.status_code
        self.text = response.text
        body = response.json() if response.text else {}
        #: the part a module acts on: its status and, maybe, a command
        self.told = body.get("result", {}) if json_rpc else body

    @property
    def command(self):
        return self.told.get("cmd")


class ConversationCase(HttpCase):
    URL = "/hr/rfid/event"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The upkeep the schedule queues by itself is not part of any story
        # here; the tests that are about it queue it themselves.
        for cron in (
            "hr_rfid.hr_rfid_read_ctrl_status_cron",
            "hr_rfid.hr_rfid_sync_ctrl_clock_cron",
            "hr_rfid.hr_rfid_set_card_active_inactive_status",
        ):
            cls.env.ref(cron).active = False
        cls.Command = cls.env["hr.rfid.command"]
        cls.SystemEvent = cls.env["hr.rfid.event.system"]
        cls.UserEvent = cls.env["hr.rfid.event.user"]
        # An old module (10.3) and a new one (100.1): the serial tells them
        # apart, and decides the shape of every reply.
        cls.old_door, cls.old_in, cls.old_out = one_door(
            cls.env,
            "Old",
            7711,
            33,
            serial="234711",
            hw_version="10.3",
            version="1.35",
            key="A1B2",
        )
        cls.new_door, cls.new_in, cls.new_out = one_door(
            cls.env, "New", 7712, 34, serial="400712", key="C3D4"
        )
        cls.old = cls.old_door.controller_id.webstack_id
        cls.new = cls.new_door.controller_id.webstack_id
        cls.old_ctrl = cls.old_door.controller_id
        cls.new_ctrl = cls.new_door.controller_id
        cls.employee = cls.env["hr.employee"].create({"name": "Somebody With A Badge"})
        cls.card = (
            cls.env["hr.rfid.card"]
            .with_context(no_hardware_commands=True)
            .create(
                {
                    "number": "0012340001",
                    "employee_id": cls.employee.id,
                    "company_id": cls.env.company.id,
                }
            )
        )

    # -- what a module sends -------------------------------------------
    def say(self, module, body, key=None, json_rpc=False, expect_failure=False):
        """Post one report as this module and return what it is told.

        :param key: the key shown; the module's own by default, ``False`` to
                    send no key at all
        """
        serial = module if isinstance(module, str) else module.serial
        payload = dict(body, convertor=serial)
        if key is not False:
            payload["key"] = key if key is not None else module.key
        if json_rpc:
            payload = {"jsonrpc": "2.0", "id": 7, "params": payload}
        before = self.SystemEvent.search([], order="id desc", limit=1).id or 0
        response = self.url_open(
            self.URL,
            data=json.dumps(payload),
            timeout=60,
            headers={"Content-Type": "application/json"},
        )
        self.env.invalidate_all()
        crashed = self.SystemEvent.search(
            [
                ("id", ">", before),
                ("error_description", "like", "Traceback (most recent call last)"),
            ]
        )
        if not expect_failure:
            self.assertFalse(
                crashed, "the report failed here:\n%s" % crashed[:1].error_description
            )
            # A failure that never reached the handlers leaves no record at
            # all - it is rolled back with everything else - only this status.
            self.assertEqual(
                response.status_code,
                200,
                "the report failed outside the handlers:\n%s" % response.text[:2000],
            )
        reply = Reply(response, json_rpc)
        reply.failure = crashed
        return reply

    def heartbeat(self, module, **how):
        return self.say(module, {"FW": module.version or "1.35", "heartbeat": 1}, **how)

    def event(self, ctrl, event_n, **how):
        return self.event_from(ctrl.webstack_id, ctrl.ctrl_id, event_n, **how)

    def event_from(
        self, module, ctrl_number, event_n, card=NO_CARD, reader=1, when=None, **how
    ):
        """An event as the module reports it: in its own date format and local time."""
        local = (when or fields.Datetime.now()) + module._get_tz_offset()
        date_format, time_format = module.time_format.split(" ")
        return self.say(
            module,
            {
                "event": {
                    "id": ctrl_number,
                    "cmd": "FA",
                    "tos": 9,
                    "bos": 8,
                    "err": 0,
                    "event_n": event_n,
                    "reader": reader,
                    "card": card,
                    "dt": "0000",
                    "date": local.strftime(date_format),
                    "time": local.strftime(time_format),
                    "day": local.isoweekday(),
                }
            },
            **how,
        )

    def passage(self, ctrl, reader, when=None, card=None):
        return self.event(
            ctrl,
            GRANTED_AT_READER[reader],
            card=card or self.card.number,
            reader=reader,
            when=when,
        )

    def answer(self, ctrl, command, error=0, data="", **how):
        """The controller's answer to the command the module was just handed."""
        return self.say(
            ctrl.webstack_id,
            {
                "response": {
                    "id": ctrl.ctrl_id,
                    "c": command["c"],
                    "e": error,
                    "d": data,
                }
            },
            **how,
        )

    # -- what the operator set up --------------------------------------
    def a_change_of_access(self, ctrl, card_number="0012340001"):
        """A card's rights changed: the command the card screens queue."""
        return self.Command.create_d1_cmd(
            ctrl.webstack_id.id, ctrl.id, card_number, "0000", "00000000", 3, 3, False
        )

    def grow_old(self, command):
        """Time passes: the module had long enough to answer."""
        command.sent_at = fields.Datetime.now() - timedelta(
            seconds=CMD_ANSWER_TIMEOUT_S + 5
        )

    def out(self, module):
        return self.Command.search(
            [("webstack_id", "=", module.id), ("status", "=", "Process")]
        )

    def log_of(self, ctrl):
        return self.SystemEvent.search([("controller_id", "=", ctrl.id)], order="id")


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestTheReplyIsInTheModulesOwnLanguage(ConversationCase):
    def test_an_old_module_with_nothing_to_do_gets_an_empty_reply(self):
        """A 10.3 module that reports in and has nothing waiting is answered with nothing."""
        reply = self.heartbeat(self.old)

        self.assertEqual((reply.http_status, reply.text), (200, ""))

    def test_an_old_module_gets_its_command_and_nothing_else(self):
        """A 10.3 module reads a command by its place in the reply: the reply is the command only."""
        self.a_change_of_access(self.old_ctrl)

        reply = self.heartbeat(self.old)

        self.assertEqual(list(json.loads(reply.text)), ["cmd"])
        self.assertEqual((reply.command["id"], reply.command["c"]), (33, "D1"))

    def test_real_time_settings_never_reach_an_old_module(self):
        """NEGATIVE: the settings of the real-time connection stay out of a 10.3 reply.

        They are meant for a 100.1. Somebody pressing Enable real-time on an
        old module must not change what that module reads from then on.
        """
        self.old.action_ws_enable()
        self.assertTrue(self.old.ws_provision_pending)
        self.a_change_of_access(self.old_ctrl)

        reply = self.heartbeat(self.old)

        self.assertEqual(list(json.loads(reply.text)), ["cmd"])
        self.assertNotIn("ws", reply.text)

    def test_a_new_module_is_told_the_status_in_plain_json(self):
        """A 100.1 module gets a plain JSON reply: its status, and the command next to it."""
        self.assertEqual(self.heartbeat(self.new).told, {"status": 200})

        self.a_change_of_access(self.new_ctrl)
        reply = self.heartbeat(self.new)

        self.assertEqual(reply.told["status"], 200)
        self.assertEqual((reply.command["id"], reply.command["c"]), (34, "D1"))

    def test_a_new_module_gets_its_real_time_settings(self):
        """Enable real-time on a 100.1, and its next report brings the settings back."""
        self.new.action_ws_enable()

        told = self.heartbeat(self.new).told

        self.assertEqual(told["status"], 200)
        self.assertEqual(told["ws"]["en"], 1)
        self.assertEqual(told["ws"]["db"], self.env.cr.dbname)

    def test_a_module_speaking_json_rpc_is_answered_in_json_rpc(self):
        """A report wrapped in JSON-RPC is answered wrapped the same, under its own id."""
        self.a_change_of_access(self.new_ctrl)

        reply = self.heartbeat(self.new, json_rpc=True)

        body = json.loads(reply.text)
        self.assertEqual((body["jsonrpc"], body["id"]), ("2.0", 7))
        self.assertEqual(reply.told["status"], 200)
        self.assertEqual(reply.command["c"], "D1")

    def test_a_shape_nobody_handles_is_accepted_and_dropped(self):
        """NEGATIVE: a device that is not one of ours is not left repeating itself."""
        response = self.url_open(
            self.URL,
            data=json.dumps({"serial": "x", "events": []}),
            timeout=60,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.json(), {"status": 200})


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestWhoIsListenedTo(ConversationCase):
    def setUp(self):
        super().setUp()
        self.params = self.env["ir.config_parameter"].sudo()

    def test_a_wrong_key_is_refused_and_leaves_no_trace_of_contact(self):
        """NEGATIVE: a report with the wrong key is refused, said so in the log, and changes nothing."""
        self.a_change_of_access(self.new_ctrl)
        before = self.SystemEvent.search_count([("webstack_id", "=", self.new.id)])

        reply = self.heartbeat(self.new, key="FFFF")

        self.assertEqual(reply.told, {"status": 400})
        self.assertFalse(
            self.new.updated_at, "a stranger must not make the module look alive"
        )
        self.assertFalse(
            self.out(self.new), "and is not handed the commands of the module"
        )
        self.assertEqual(
            self.SystemEvent.search_count([("webstack_id", "=", self.new.id)]),
            before + 1,
        )

    def test_a_module_nobody_registered_is_refused(self):
        """NEGATIVE: an unknown module is refused and not created, unless the site says to take new ones."""
        self.params.set_param("hr_rfid.save_new_webstacks", "False")

        reply = self.say("499001", {"FW": "1.44", "heartbeat": 1}, key="E5F6")

        self.assertEqual(reply.told, {"status": 400})
        self.assertFalse(
            self.env["hr.rfid.webstack"].search([("serial", "=", "499001")])
        )

    def test_a_new_module_is_registered_and_waits_for_the_operator(self):
        """With "save new modules" on, a module that reports for the first time is registered - switched off.

        It is written down with the key it showed, so the operator finds it
        in the list. It is listened to only once they switch it on.
        """
        self.params.set_param("hr_rfid.save_new_webstacks", "True")

        reply = self.say("499002", {"FW": "1.44", "heartbeat": 1}, key="E5F6")

        module = (
            self.env["hr.rfid.webstack"]
            .with_context(active_test=False)
            .search([("serial", "=", "499002")])
        )
        self.assertEqual((module.key, module.active), ("E5F6", False))
        self.assertEqual(reply.told["status"], 400)
        self.assertTrue(
            module.ws_enabled, "a 100.1 is set to come up on the real-time connection"
        )

    def test_a_module_switched_off_here_is_refused(self):
        """NEGATIVE: a module the operator archived is not listened to, and the log says why."""
        self.new.active = False

        reply = self.passage(self.new_ctrl, 1)

        self.assertEqual(reply.told, {"status": 400})
        self.assertFalse(self.UserEvent.search([("card_id", "=", self.card.id)]))
        self.assertIn(
            "Webstack is not active",
            self.SystemEvent.search([("webstack_id", "=", self.new.id)]).mapped(
                "error_description"
            ),
        )

    def test_the_factory_key_is_accepted_but_never_kept(self):
        """A module still on the factory key 0000 works, and 0000 is not stored as its key."""
        self.old.key = False

        reply = self.heartbeat(self.old, key="0000")

        self.assertEqual((reply.http_status, reply.text), (200, ""))
        self.assertFalse(self.old.key)
        self.assertTrue(self.old.updated_at)

    def test_a_module_without_a_key_here_takes_the_real_one_it_shows(self):
        """A module registered without a key is given the key it reports with, the first time."""
        self.new.key = False

        self.heartbeat(self.new, key="9A8B")

        self.assertEqual(self.new.key, "9A8B")


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestAChangeReachesTheController(ConversationCase):
    def test_a_change_goes_out_and_the_next_one_follows_the_answer(self):
        """Two changes of access: the first goes out with the next report, the second with its answer."""
        first = self.a_change_of_access(self.new_ctrl, "0012340001")
        second = self.a_change_of_access(self.new_ctrl, "0012340002")

        handed = self.heartbeat(self.new).command
        self.assertEqual(handed["c"], "D1")
        self.assertEqual((first.status, second.status), ("Process", "Wait"))
        self.assertTrue(first.sent_at)

        after = self.answer(self.new_ctrl, handed)

        self.assertEqual(first.status, "Success")
        self.assertTrue(first.ex_timestamp)
        self.assertEqual(after.command["c"], "D1")
        self.assertEqual(second.status, "Process")

    def test_reports_in_a_burst_do_not_send_the_command_again(self):
        """A module emptying its backlog reports many times a second; the command is out once.

        Each of those reports used to get the same command again and count
        as a failed attempt, so five passages in a row gave a command up
        while the module was still carrying it out.
        """
        command = self.a_change_of_access(self.new_ctrl)
        waiting = self.a_change_of_access(self.new_ctrl, "0012340002")
        self.assertTrue(self.heartbeat(self.new).command)

        for _report in range(CMD_MAX_RETRIES + 2):
            self.assertEqual(self.passage(self.new_ctrl, 1).told, {"status": 200})
        self.assertEqual(self.heartbeat(self.new).told, {"status": 200})

        self.assertEqual((command.status, command.retries), ("Process", 0))
        self.assertEqual(waiting.status, "Wait", "and nothing else goes out next to it")

    def test_a_command_left_without_an_answer_goes_out_again(self):
        """When the module had its time and did not answer, the command is handed over once more."""
        command = self.a_change_of_access(self.new_ctrl)
        first = self.heartbeat(self.new).command
        self.grow_old(command)

        again = self.heartbeat(self.new).command

        self.assertEqual(again, first)
        self.assertEqual((command.status, command.retries), ("Process", 1))

    def test_a_command_nobody_answers_is_given_up_and_the_operator_is_told(self):
        """After its attempts a command is closed with the reason, the queue moves on, and the log says it.

        The operator changed a card's rights. The controller never took it.
        They must learn that from the controller's log, with the card - not
        by opening the list of commands and finding "no error".
        """
        dead = self.a_change_of_access(self.new_ctrl, "0012340001")
        next_one = self.a_change_of_access(self.new_ctrl, "0012340002")
        self.heartbeat(self.new)
        for attempt in range(1, CMD_MAX_RETRIES + 1):
            self.grow_old(dead)
            self.heartbeat(self.new)
            self.assertEqual((dead.status, dead.retries), ("Process", attempt))
        self.grow_old(dead)

        reply = self.heartbeat(self.new)

        self.assertEqual((dead.status, dead.error), ("Failure", "30"))
        self.assertTrue(dead.ex_timestamp)
        self.assertEqual(
            next_one.status, "Process", "the next change goes out in the same reply"
        )
        self.assertEqual(reply.command["c"], "D1")
        said = self.log_of(self.new_ctrl).mapped("error_description")
        self.assertTrue(
            [
                line
                for line in said
                if "0012340001" in line and "No answer came" in line
            ],
            "nothing in the controller's log about the card: %s" % said,
        )

    def test_the_module_saying_the_controller_is_silent_is_recorded_as_that(self):
        """When the module reports that the controller did not answer, the command says so when it is closed."""
        command = self.a_change_of_access(self.new_ctrl)
        handed = self.heartbeat(self.new).command
        for attempt in range(1, CMD_MAX_RETRIES + 1):
            handed = self.answer(self.new_ctrl, handed, error=20).command
            self.assertEqual((command.status, command.retries), ("Process", attempt))

        self.answer(self.new_ctrl, handed, error=20)

        self.assertEqual((command.status, command.error), ("Failure", "20"))

    def test_a_module_that_is_momentarily_full_gets_the_command_again(self):
        """ "Try again" from the module is not a failure: the command stays in the queue."""
        command = self.a_change_of_access(self.new_ctrl)
        handed = self.heartbeat(self.new).command

        reply = self.answer(self.new_ctrl, handed, error=24)

        self.assertEqual(reply.command, handed, "it is handed over again")
        self.assertEqual((command.status, command.retries), ("Process", 1))

    def test_a_command_out_since_before_the_upgrade_does_not_block_the_queue(self):
        """A command that was out before the time of sending was recorded is overdue, not fresh for ever."""
        command = self.a_change_of_access(self.new_ctrl)
        first = self.heartbeat(self.new).command
        command.sent_at = False

        again = self.heartbeat(self.new).command

        self.assertEqual(again, first)
        self.assertEqual((command.status, command.retries), ("Process", 1))

    def test_a_time_of_sending_ahead_of_the_clock_does_not_hold_the_queue(self):
        """NEGATIVE: a command stamped later than now (the server clock was set back) is not waited for until then."""
        command = self.a_change_of_access(self.new_ctrl)
        first = self.heartbeat(self.new).command
        command.sent_at = fields.Datetime.now() + timedelta(hours=1)

        again = self.heartbeat(self.new).command

        self.assertEqual(again, first)
        self.assertEqual((command.status, command.retries), ("Process", 1))

    def test_a_command_already_given_up_is_not_given_up_twice(self):
        """NEGATIVE: closing a command that is already closed writes no second line in the controller's log."""
        command = self.a_change_of_access(self.new_ctrl)
        self.heartbeat(self.new)
        command._close_unanswered()
        said = len(self.log_of(self.new_ctrl))

        command._close_unanswered()

        self.assertEqual(len(self.log_of(self.new_ctrl)), said)

    def test_while_a_door_is_being_answered_nothing_else_goes_out(self):
        """NEGATIVE: an overdue command is not handed over again next to a door's answer that is still out.

        A card shown at a door is answered at once, even while a command is
        out. From then on the module has two, and a third - or the first one
        again - must wait until the door's answer has had its time.
        """
        change = self.a_change_of_access(self.new_ctrl)
        self.heartbeat(self.new)
        self.event(self.new_ctrl, 64, card=self.card.number)
        door_answer = self.out(self.new) - change
        self.grow_old(change)

        self.assertEqual(self.heartbeat(self.new).told, {"status": 200})
        self.assertEqual((change.status, change.retries), ("Process", 0))

        self.grow_old(door_answer)
        later = self.heartbeat(self.new)

        self.assertEqual(door_answer.status, "Failure")
        self.assertEqual(later.command["c"], "D1")
        self.assertEqual((change.status, change.retries), ("Process", 1))

    def test_an_error_nobody_has_a_name_for_closes_the_command_and_not_the_conversation(
        self,
    ):
        """NEGATIVE: an error code that is not in the list fails the command, never the reply."""
        command = self.a_change_of_access(self.new_ctrl)
        handed = self.heartbeat(self.new).command

        reply = self.answer(self.new_ctrl, handed, error=77)

        self.assertEqual(reply.told, {"status": 200})
        self.assertEqual((command.status, command.error), ("Failure", "-1"))

    def test_an_answer_to_nothing_is_noted_and_brings_no_command(self):
        """NEGATIVE: an answer to a command that was never sent is written down, and nothing is handed out for it."""
        waiting = self.a_change_of_access(self.new_ctrl)

        reply = self.answer(self.new_ctrl, {"c": "F0"})

        self.assertEqual(reply.told, {"status": 200})
        self.assertEqual(waiting.status, "Wait")
        self.assertIn(
            "Controller sent us a response to a command we never sent",
            self.log_of(self.new_ctrl).mapped("error_description"),
        )


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestUpkeepAndAnswersOfTheMoment(ConversationCase):
    def test_the_controller_is_given_the_time_of_its_own_place(self):
        """The clock written to a controller is the time on the wall where its module is."""
        self.new_ctrl.synchronize_clock_cmd()

        data = self.heartbeat(self.new).command["d"]

        there = fields.Datetime.context_timestamp(
            self.new.with_context(tz=self.new.tz), fields.Datetime.now()
        )
        second, minute, hour, weekday, day, month, year = (
            int(data[i : i + 2]) for i in range(0, 14, 2)
        )
        self.assertEqual(
            (hour, weekday, day, month, year),
            (there.hour, there.isoweekday(), there.day, there.month, there.year % 100),
        )
        self.assertLessEqual(
            abs(minute * 60 + second - there.minute * 60 - there.second), 60
        )

    def test_a_clock_nobody_answers_is_not_sent_again_and_holds_nothing_up(self):
        """Routine upkeep is tried once: left without an answer it steps aside for the next command.

        The clock is set every few hours anyway. A controller that does not
        answer it used to cost six reports of the module each time, with
        every change of access waiting behind it - on a site whose module
        reports rarely, a day.
        """
        clock = self.new_ctrl.synchronize_clock_cmd()
        change = self.a_change_of_access(self.new_ctrl)
        self.assertEqual(self.heartbeat(self.new).command["c"], "D7")
        self.grow_old(clock)

        reply = self.heartbeat(self.new)

        self.assertEqual(
            (clock.status, clock.error, clock.retries), ("Failure", "30", 0)
        )
        self.assertEqual(reply.command["c"], "D1")
        self.assertEqual(change.status, "Process")

    def test_a_controller_that_powers_up_gets_the_clock_at_once(self):
        """A controller that restarts is given the time in the answer to that very report."""
        reply = self.event(self.new_ctrl, 30)

        self.assertEqual(reply.told["status"], 200)
        self.assertEqual(reply.command["c"], "D7")
        self.assertEqual(len(self.out(self.new)), 1)

    def test_a_power_up_does_not_put_a_second_command_out(self):
        """NEGATIVE: while a command is out, the clock for a restarted controller waits its turn.

        Two commands out at once cannot be told apart when the answers come
        back, and the first was sent again in place of the second.
        """
        change = self.a_change_of_access(self.new_ctrl)
        self.heartbeat(self.new)

        reply = self.event(self.new_ctrl, 30)

        self.assertEqual(reply.told, {"status": 200})
        self.assertEqual(self.out(self.new), change)
        self.assertEqual(
            self.Command.search(
                [("controller_id", "=", self.new_ctrl.id), ("cmd", "=", "D7")]
            ).status,
            "Wait",
        )

    def test_a_door_left_open_has_its_state_read_one_reading_at_a_time(self):
        """A door reported open twice in a row gets one reading out, not two side by side."""
        first = self.event(self.new_ctrl, 25)
        second = self.event(self.new_ctrl, 25)

        self.assertEqual(first.command["c"], "B3")
        self.assertEqual(second.told, {"status": 200})
        self.assertEqual(len(self.out(self.new)), 1)

    def test_an_output_switched_from_the_software_has_its_state_read(self):
        """A controller that reports an output switched from here has its state read, one reading at a time."""
        first = self.event(self.new_ctrl, 31)
        second = self.event(self.new_ctrl, 31)

        self.assertEqual(first.command["c"], "B3")
        self.assertEqual(second.told, {"status": 200})
        self.assertEqual(len(self.out(self.new)), 1)

    def test_a_controller_nobody_knows_is_asked_what_it_is(self):
        """A report from a controller that is not registered creates it and asks for its description."""
        reply = self.event_from(self.new, 77, 3, card=self.card.number)

        controller = self.env["hr.rfid.ctrl"].search(
            [("webstack_id", "=", self.new.id), ("ctrl_id", "=", 77)]
        )
        self.assertTrue(controller)
        self.assertEqual(
            reply.told["status"],
            400,
            "the report is not accepted until the controller is known",
        )
        self.assertEqual((reply.command["id"], reply.command["c"]), (77, "F0"))

    def test_may_this_card_pass_is_answered_once_and_never_later(self):
        """NEGATIVE: the answer to a card shown at a door is not sent again minutes afterwards.

        A controller that keeps its cards here asks at the moment the card
        is shown. If that answer got lost, sending it with a later report
        would release a door for somebody who has long walked away.
        """
        reply = self.event(self.new_ctrl, 64, card=self.card.number)
        self.assertEqual(reply.command["c"], "DB")
        answer = self.out(self.new)
        self.assertTrue(answer.single_attempt)
        self.grow_old(answer)

        later = self.heartbeat(self.new)

        self.assertEqual(later.told, {"status": 200})
        self.assertEqual((answer.status, answer.retries), ("Failure", 0))

    def test_a_door_answer_the_controller_did_not_take_is_never_offered_again(self):
        """NEGATIVE: "the controller is silent" does not bring the answer to a card back in the same reply."""
        reply = self.event(self.new_ctrl, 64, card=self.card.number)
        answer = self.out(self.new)

        after = self.answer(self.new_ctrl, reply.command, error=20)

        self.assertEqual(after.told, {"status": 200})
        self.assertEqual(
            (answer.status, answer.error, answer.retries), ("Failure", "20", 0)
        )
        self.assertEqual(self.heartbeat(self.new).told, {"status": 200})

    def test_a_door_answer_the_module_had_no_room_for_is_not_kept_for_later(self):
        """NEGATIVE: "try again" from the module does not put the answer to a card back in the queue."""
        reply = self.event(self.new_ctrl, 64, card=self.card.number)
        answer = self.out(self.new)

        after = self.answer(self.new_ctrl, reply.command, error=24)

        self.assertEqual(after.told, {"status": 200})
        self.assertEqual((answer.status, answer.error), ("Failure", "24"))
        self.assertEqual(self.heartbeat(self.new).told, {"status": 200})

    def test_a_card_at_a_controller_not_yet_described_waits_for_the_description(self):
        """A card used at a controller that has not said what it is yet is kept by the module, not thrown away.

        The controller is known by its number only until it answers what it
        is; it has no readers before that. The passage used to be accepted
        and dropped with "could not find a reader".
        """
        first = self.event_from(self.new, 77, 3, card=self.card.number)
        self.assertEqual(first.command["c"], "F0")
        controller = self.env["hr.rfid.ctrl"].search(
            [("webstack_id", "=", self.new.id), ("ctrl_id", "=", 77)]
        )

        again = self.event_from(self.new, 77, 3, card=self.card.number)

        self.assertEqual(again.told["status"], 400, "the module keeps the passage")
        said = self.log_of(controller)
        self.assertNotIn(
            "Could not find a reader with that id", said.mapped("error_description")
        )
        self.assertIn(
            self.card.number,
            said[-1:].input_js or "",
            "an old module cannot be told to keep it, so it is written down",
        )

    def test_a_controller_that_never_describes_itself_does_not_hold_the_module(self):
        """NEGATIVE: once the question "what are you" went unanswered, the module's reports are not held back.

        One controller that will not say what it is must not stop the
        module from reporting everything else. Its passages are noted and
        accepted; the operator asks it again from its form.
        """
        self.event_from(self.new, 77, 3, card=self.card.number)
        self.out(self.new)._close_unanswered()

        reply = self.event_from(self.new, 77, 3, card=self.card.number)

        self.assertEqual(reply.told, {"status": 200})
        controller = self.env["hr.rfid.ctrl"].search(
            [("webstack_id", "=", self.new.id), ("ctrl_id", "=", 77)]
        )
        self.assertIn(
            "Could not find a reader with that id",
            self.log_of(controller).mapped("error_description"),
        )

    def test_a_controller_that_stops_answering_its_upkeep_is_reported_once(self):
        """The log says when a controller stops answering its upkeep - once, not at every clock setting after.

        On a quiet site the clock and the state reading are the only
        commands there are, so their silence is the only sign that a
        controller is gone from its line.
        """
        for _round in range(3):
            clock = self.new_ctrl.synchronize_clock_cmd()
            self.heartbeat(self.new)
            self.grow_old(clock)
            self.heartbeat(self.new)
            self.assertEqual(clock.status, "Failure")

        said = self.log_of(self.new_ctrl).filtered(
            lambda line: "No answer came" in line.error_description
        )
        self.assertEqual(
            said.mapped("occurrences"), [1], said.mapped("error_description")
        )


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestReportsNobodyActsOn(ConversationCase):
    def test_an_alarm_zone_delay_is_kept_and_accepted(self):
        """A report the system does nothing with is still a fact of the site: logged, and accepted.

        These two used to be answered with an error. A module that keeps a
        report until it is accepted then sends the same one for ever, and
        nothing that happened after it.
        """
        for event_n in (27, 28):
            reply = self.event(self.new_ctrl, event_n)

            self.assertEqual(reply.told, {"status": 200})
            self.assertEqual(self.log_of(self.new_ctrl)[-1:].event_action, str(event_n))

    def test_a_report_of_an_unknown_kind_is_kept_and_accepted(self):
        """NEGATIVE: an event number nobody has heard of never becomes an error to the module."""
        reply = self.event(self.new_ctrl, 63)

        self.assertEqual(reply.told, {"status": 200})
        self.assertIn(
            "Unknown event", self.log_of(self.new_ctrl)[-1:].error_description
        )

    def test_a_date_no_calendar_has_is_logged_and_let_go(self):
        """A report with a time that cannot be read is written down as it came and accepted."""
        reply = self.say(
            self.new,
            {
                "event": {
                    "id": 34,
                    "cmd": "FA",
                    "tos": 9,
                    "bos": 8,
                    "err": 0,
                    "event_n": 3,
                    "reader": 1,
                    "card": self.card.number,
                    "dt": "0000",
                    "date": "99.99.99",
                    "time": "25:61:61",
                    "day": 1,
                }
            },
        )

        self.assertEqual(reply.told, {"status": 200})
        self.assertIn(
            "invalid date or time",
            self.SystemEvent.search(
                [("webstack_id", "=", self.new.id)], order="id desc", limit=1
            ).error_description,
        )
        self.assertFalse(self.UserEvent.search([("card_id", "=", self.card.id)]))


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestWhenItFailsHere(ConversationCase):
    def setUp(self):
        super().setUp()
        # The site does not keep its communication: what survives a failure
        # survives because it failed, not because everything is kept.
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_rfid.save_webstack_communications", "false"
        )

    def _failing(self, error=None):
        return patch.object(
            type(self.env["hr.rfid.webstack"]),
            "parse_heartbeat",
            side_effect=error or ValueError("something is wrong on this side"),
        )

    def test_any_failure_keeps_the_report_and_says_where(self):
        """Whatever goes wrong while a report is handled, the module is told and the report is kept with the place."""
        for error in (ValueError("a wrong value"), TypeError("a wrong kind")):
            with self.subTest(error=type(error).__name__), self._failing(error):
                reply = self.heartbeat(self.new, expect_failure=True)

                self.assertEqual(reply.told, {"status": 500})
                self.assertIn("Traceback", reply.failure.error_description)
                self.assertIn(str(error), reply.failure.error_description)
                self.assertIn(self.new.serial, reply.failure.input_js)
                self.assertNotIn(
                    self.new.key,
                    reply.failure.input_js,
                    "the copy that people read does not carry the module's key",
                )

    def test_a_failure_in_the_database_is_recorded_like_any_other(self):
        """An error from the database does not take the record of the failure down with it.

        After such an error nothing more can be written until the work on
        the report is undone. It was not undone, so the record of the
        failure failed too, and only the server log knew.
        """

        def breaks_in_the_database(module, post_data):
            module.env.cr.execute("SELECT 1 / 0")

        with patch.object(
            type(self.env["hr.rfid.webstack"]),
            "parse_heartbeat",
            breaks_in_the_database,
        ):
            reply = self.heartbeat(self.new, expect_failure=True)

        self.assertEqual(reply.told, {"status": 500})
        self.assertIn("division by zero", reply.failure.error_description)
        self.assertIn(self.new.serial, reply.failure.input_js)

    def test_a_report_that_failed_half_way_leaves_nothing_half_done(self):
        """NEGATIVE: what a failed report had already changed is undone; only the record of the failure stays."""

        def changes_then_fails(module, post_data):
            module.name = "Changed half way"
            raise ValueError("and then it failed")

        with patch.object(
            type(self.env["hr.rfid.webstack"]), "parse_heartbeat", changes_then_fails
        ):
            self.heartbeat(self.new, expect_failure=True)

        self.assertNotEqual(self.new.name, "Changed half way")

    def test_a_report_with_no_key_is_refused_and_not_kept(self):
        """NEGATIVE: a report that shows no key is refused like a wrong key, and what it carried is not written down.

        The endpoint is open to anyone who knows a serial. It used to fail
        on such a report instead of refusing it. What a stranger posts is
        kept only on a site that keeps all its communication.
        """
        reply = self.say(self.new, {"heartbeat": 1, "junk": "x" * 500}, key=False)

        self.assertEqual(reply.told, {"status": 400})
        noted = self.SystemEvent.search(
            [("webstack_id", "=", self.new.id)], order="id desc", limit=1
        )
        self.assertEqual(
            noted.error_description, "Webstack key and key in json did not match"
        )
        self.assertFalse(noted.input_js)

    def test_a_kept_report_has_a_limit(self):
        """NEGATIVE: a failed report of any size is kept only up to a limit."""
        with self._failing():
            reply = self.say(
                self.new,
                {"FW": "1.44", "heartbeat": 1, "junk": "x" * 50000},
                expect_failure=True,
            )

        self.assertLessEqual(len(reply.failure.input_js), 20000)
        self.assertIn('"heartbeat": 1', reply.failure.input_js)

    def test_a_new_module_is_told_and_the_report_survives(self):
        """When handling a report fails here, a 100.1 is told so, and the report is kept with where it failed."""
        with self._failing():
            reply = self.heartbeat(self.new, expect_failure=True)

        self.assertEqual(reply.told, {"status": 500})
        self.assertIn(
            "something is wrong on this side", reply.failure.error_description
        )
        self.assertIn(self.new.serial, reply.failure.input_js)

    def test_an_old_module_cannot_be_told_so_the_log_is_all_there_is(self):
        """A 10.3 reads an empty reply either way, so what it reported must survive in the log.

        This is the limit of the old module, not a choice made here: it has
        no way to read "that went wrong, keep it". The record of the report
        is therefore the one place it can be recovered from.
        """
        with self._failing():
            reply = self.heartbeat(self.old, expect_failure=True)

        self.assertEqual((reply.http_status, reply.text), (200, ""))
        self.assertIn("Traceback", reply.failure.error_description)
        self.assertIn(self.old.serial, reply.failure.input_js)


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestALatePassage(ConversationCase):
    """A zone knows who is inside. A module that was out of touch reports days late."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.zone = cls.env["hr.rfid.zone"].create(
            {
                "name": "The Floor",
                "company_id": cls.env.company.id,
                "door_ids": [(4, cls.new_door.id)],
            }
        )

    def test_an_entry_that_arrives_late_does_not_put_back_somebody_who_left(self):
        """The person came in, and left. Their entry of two days ago, arriving now, leaves them outside.

        It did put them back: the zone showed somebody inside who had gone,
        and anti-passback told the other doors to let that card out only.
        """
        now = fields.Datetime.now()
        self.passage(self.new_ctrl, 1, when=now - timedelta(minutes=10))
        self.assertIn(self.employee, self.zone.employee_ids)
        self.passage(self.new_ctrl, 2, when=now - timedelta(minutes=5))
        self.assertNotIn(self.employee, self.zone.employee_ids)

        self.passage(self.new_ctrl, 1, when=now - timedelta(days=2))

        self.assertNotIn(self.employee, self.zone.employee_ids)
        self.assertEqual(
            self.UserEvent.search_count([("card_id", "=", self.card.id)]),
            3,
            "the late passage itself is recorded like any other",
        )

    def test_an_exit_that_arrives_late_does_not_take_out_somebody_who_came_back(self):
        """The person came in, left and came back. Their exit of two days ago, arriving now, leaves them inside."""
        now = fields.Datetime.now()
        self.passage(self.new_ctrl, 1, when=now - timedelta(minutes=20))
        self.passage(self.new_ctrl, 2, when=now - timedelta(minutes=15))
        self.passage(self.new_ctrl, 1, when=now - timedelta(minutes=5))
        self.assertIn(self.employee, self.zone.employee_ids)

        self.passage(self.new_ctrl, 2, when=now - timedelta(days=2))

        self.assertIn(self.employee, self.zone.employee_ids)

    def test_a_visitors_late_entry_does_not_put_them_back(self):
        """The same for somebody who is not an employee: a visitor who left stays out."""
        visitor = self.env["res.partner"].create({"name": "A Visitor"})
        card = (
            self.env["hr.rfid.card"]
            .with_context(no_hardware_commands=True)
            .create(
                {
                    "number": "0012340009",
                    "contact_id": visitor.id,
                    "company_id": self.env.company.id,
                }
            )
        )
        now = fields.Datetime.now()
        self.passage(
            self.new_ctrl, 1, when=now - timedelta(minutes=10), card=card.number
        )
        self.assertIn(visitor, self.zone.contact_ids)
        self.passage(
            self.new_ctrl, 2, when=now - timedelta(minutes=5), card=card.number
        )

        self.passage(self.new_ctrl, 1, when=now - timedelta(days=2), card=card.number)

        self.assertNotIn(visitor, self.zone.contact_ids)

    def test_a_passage_a_few_minutes_old_is_taken_as_it_comes(self):
        """NEGATIVE: clocks that differ by minutes do not make a passage history - what happens now moves the zone.

        Two controllers never show the same minute. An exit stamped a
        little before the entry that was reported first is still the last
        thing the person did.
        """
        now = fields.Datetime.now()
        self.passage(self.new_ctrl, 1, when=now - timedelta(minutes=2))
        self.assertIn(self.employee, self.zone.employee_ids)

        self.passage(self.new_ctrl, 2, when=now - timedelta(minutes=5))

        self.assertNotIn(self.employee, self.zone.employee_ids)

    def test_a_clock_that_runs_ahead_does_not_freeze_the_zone(self):
        """NEGATIVE: a passage stamped in the future does not overtake everything the person does after it.

        One controller with its clock a day ahead would otherwise keep
        people where it last saw them until that day comes.
        """
        now = fields.Datetime.now()
        self.passage(self.new_ctrl, 1, when=now + timedelta(days=1))
        self.assertIn(self.employee, self.zone.employee_ids)

        self.passage(self.new_ctrl, 2, when=now - timedelta(hours=1))

        self.assertNotIn(self.employee, self.zone.employee_ids)

    def test_a_late_passage_with_nothing_after_it_still_says_where_the_person_is(self):
        """NEGATIVE: late alone is not history - the newest passage known moves the person, however old."""
        self.passage(self.new_ctrl, 1, when=fields.Datetime.now() - timedelta(days=2))

        self.assertIn(self.employee, self.zone.employee_ids)


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestRealTimeIsOfferedWhereItWorks(ConversationCase):
    def _enable_is_hidden_for(self, module):
        arch = self.env["hr.rfid.webstack"].get_view(
            self.env.ref("hr_rfid.hr_rfid_webstack_view_form").id, "form"
        )["arch"]
        button = etree.fromstring(arch).xpath("//button[@name='action_ws_enable']")[0]
        return bool(
            safe_eval(
                button.get("invisible"),
                {"ws_enabled": module.ws_enabled, "hw_version": module.hw_version},
            )
        )

    def test_the_button_is_there_for_a_100_1_and_not_for_a_10_3(self):
        """The form offers Enable real-time on a module that can use it, and only there."""
        self.assertFalse(self._enable_is_hidden_for(self.new))
        self.assertTrue(
            self._enable_is_hidden_for(self.old),
            "a 10.3 has no real-time connection to enable",
        )


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestRefusalsTheControllerReports(ConversationCase):
    def test_a_refused_arming_by_an_unknown_card_is_kept_and_accepted(self):
        """NEGATIVE: an alarm zone refused to a card nobody knows is a line in the log, not an error.

        It used to raise, and the module was told to keep the report.
        """
        reply = self.event(self.new_ctrl, 33, card="9999999999")

        self.assertEqual(reply.told, {"status": 200})
        line = self.log_of(self.new_ctrl)[-1:]
        self.assertEqual((line.event_action, line.card_number), ("33", "9999999999"))

    def test_a_vending_machine_nobody_serves_here_is_not_an_error(self):
        """NEGATIVE: a vending machine asking for credit that nobody here answers is logged and let go.

        Asked of the model: that is where a request lands on a site without
        the vending add-on, and on a site with it when the request comes
        over the real-time connection, past the add-on's own route. The log
        says which of the two it was.
        """
        self.new_ctrl.hw_version = "16"

        told = self.new.with_context(ws_skip_piggyback=True)._hw_parse_event(
            {
                "convertor": self.new.serial,
                "event": {
                    "id": 34,
                    "cmd": "FA",
                    "tos": 9,
                    "bos": 8,
                    "err": 0,
                    "event_n": 64,
                    "reader": 1,
                    "card": self.card.number,
                    "dt": "00000000000000",
                    "date": fields.Date.today().strftime("%m.%d.%y"),
                    "time": "10:00:00",
                    "day": 1,
                },
            }
        )

        self.assertEqual(told, {"status": 200})
        said = self.log_of(self.new_ctrl)[-1:].error_description
        if "hr.rfid.vending.event" in self.env:
            self.assertIn("did not reach the vending add-on", said)
            self.assertNotIn("not installed", said)
        else:
            self.assertIn("vending add-on is not installed", said)


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestTheQueueBeforeItGoesOut(ConversationCase):
    def test_the_same_upkeep_asked_twice_waits_once(self):
        """The clock asked for twice before the module reports is one command, and so is the status reading."""
        self.new_ctrl.synchronize_clock_cmd()
        self.new_ctrl.synchronize_clock_cmd()
        self.new_ctrl.read_status()
        self.new_ctrl.read_status()

        waiting = self.Command.search(
            [("controller_id", "=", self.new_ctrl.id), ("status", "=", "Wait")]
        )
        self.assertEqual(sorted(waiting.mapped("cmd")), ["B3", "D7"])
        self.assertEqual(waiting.mapped("single_attempt"), [True, True])

    def test_the_clock_schedule_reaches_the_controllers_of_working_modules_only(self):
        """NEGATIVE: the scheduled clock goes to every controller of a module that is on, and to none of one that is off."""
        self.old.active = False

        self.Command._sync_clocks()

        self.assertEqual(
            self.Command.search([("controller_id", "=", self.new_ctrl.id)]).mapped(
                "cmd"
            ),
            ["D7"],
        )
        self.assertFalse(
            self.Command.search([("controller_id", "=", self.old_ctrl.id)])
        )

    def test_a_passage_reported_twice_is_one_passage(self):
        """A module that repeats a report it already made does not make the person pass twice."""
        when = fields.Datetime.now() - timedelta(minutes=3)
        self.passage(self.new_ctrl, 1, when=when)
        self.passage(self.new_ctrl, 1, when=when)

        self.assertEqual(
            self.UserEvent.search_count([("card_id", "=", self.card.id)]), 1
        )

    def test_a_failed_command_can_be_sent_again(self):
        """A command that was given up goes back in the queue when somebody asks for it again."""
        command = self.a_change_of_access(self.new_ctrl)
        self.heartbeat(self.new)
        command.retries = CMD_MAX_RETRIES
        self.grow_old(command)
        self.heartbeat(self.new)
        self.assertEqual(command.status, "Failure")

        command.resend_action()

        self.assertEqual(
            (command.status, command.retries, command.error), ("Wait", 0, "0")
        )
        self.assertEqual(self.heartbeat(self.new).command["c"], "D1")


@tagged("post_install", "-at_install", "rfid", "rfid_conversation")
class TestAModuleOdooCanReach(ConversationCase):
    """Not behind NAT: Odoo calls the module itself instead of waiting for its report."""

    def setUp(self):
        super().setUp()
        self.new.write({"behind_nat": False, "last_ip": "10.0.0.5"})
        self.Module = type(self.env["hr.rfid.webstack"])

    def test_a_command_is_carried_out_at_once(self):
        """With the module in reach, a command is executed when it is asked for, not at the next report."""
        answered = {
            "convertor": self.new.serial,
            "response": {"id": 34, "c": "D7", "e": 0, "d": ""},
        }
        with patch.object(
            self.Module, "_execute_direct_cmd", return_value=answered
        ) as call:
            clock = self.new_ctrl.synchronize_clock_cmd()

        self.assertEqual(call.call_args.args[0]["cmd"]["c"], "D7")
        self.assertEqual(clock.status, "Success")
        self.assertEqual(
            self.heartbeat(self.new).told,
            {"status": 200},
            "nothing is left to hand over",
        )

    def test_a_module_that_does_not_pick_up_gets_it_with_its_next_report(self):
        """When the call to the module fails, the command waits and goes out the classic way."""
        with patch.object(self.Module, "_execute_direct_cmd", return_value=None):
            clock = self.new_ctrl.synchronize_clock_cmd()
        self.assertEqual(clock.status, "Wait")

        self.assertEqual(self.heartbeat(self.new).command["c"], "D7")

    def test_a_power_up_of_a_module_in_reach_gets_one_clock_not_two(self):
        """NEGATIVE: a clock already delivered to a module in reach is not handed over again in the reply."""
        answered = {
            "convertor": self.new.serial,
            "response": {"id": 34, "c": "D7", "e": 0, "d": ""},
        }
        with patch.object(self.Module, "_execute_direct_cmd", return_value=answered):
            reply = self.event(self.new_ctrl, 30)

        self.assertEqual(reply.told, {"status": 200})
        clocks = self.Command.search(
            [("controller_id", "=", self.new_ctrl.id), ("cmd", "=", "D7")]
        )
        self.assertEqual(clocks.mapped("status"), ["Success"])

    def test_a_silent_controller_on_a_module_in_reach_is_asked_again_with_the_next_report(
        self,
    ):
        """ "The controller is silent" to a command delivered at once puts it back in the queue, not out again.

        Nothing is handed over in that exchange, so marking the command as
        sent again would leave the queue waiting for an answer to nothing.
        """
        silent = {
            "convertor": self.new.serial,
            "response": {"id": 34, "c": "F0", "e": 20, "d": ""},
        }
        with patch.object(self.Module, "_execute_direct_cmd", return_value=silent):
            asked = self.new_ctrl.read_controller_information_cmd()

        self.assertEqual((asked.status, asked.retries), ("Wait", 1))
        self.assertEqual(self.heartbeat(self.new).command["c"], "F0")

## How Odoo talks to a module

How Odoo answers the reports of an RFID module and delivers its commands to the
controllers - for whoever maintains or supports this module.

### The command queue (`controllers/polimex.py`)

- **`CMD_ANSWER_TIMEOUT_S`** *(scalar)* = `15` - how long a command handed to a module may stay unanswered before it counts as lost; shared by the classic delivery and the real-time channel
- **`CMD_MAX_RETRIES`** *(scalar)* = `5` - how many times a lost command is handed over again
- **`ROUTINE_COMMANDS`** *(collection)* = `('D7', 'B3')` - the clock and the status reading: `single_attempt`, one system event when the controller stops answering them
- **`ERROR_NO_ANSWER`** = `'30'`, **`ERROR_CONTROLLER_SILENT`** = `'20'` - the reasons a command is closed for
- **`WS_CMD_REPUBLISH_TIMEOUT_S`** = `CMD_ANSWER_TIMEOUT_S` (15) and **`WS_CMD_MAX_RETRIES`** = `CMD_MAX_RETRIES` (5) in `models/hr_rfid_command_ws.py` - the real-time channel uses the same limits

### Commands in `hr.rfid.command`

- **`_next_waiting(self, webstack)`**
  - The next command to hand to a module: the oldest in `Wait`. The one rule
    for both deliveries - `hr.rfid.webstack.check_for_unsent_cmd` (the reply
    to a module's report) and the real-time channel
    (`_ws_publish_next_command`, `_ws_on_connect_sync`).
- **`_is_still_awaited(self)`**
  - True while less than `CMD_ANSWER_TIMEOUT_S` (15 s, `controllers/polimex.py`)
    has passed since `sent_at`: the module may still be carrying the command
    out. A command with no `sent_at` (from before the field existed) counts
    as overdue.
- **`_may_be_sent_again(self)`**
  - False for a `single_attempt` command and once `retries` reached
    `CMD_MAX_RETRIES` (5).
- **`_close_unanswered(self, error='30')`**
  - Gives a command up: `status='Failure'`, the reason in `error` ('30' no
    answer from the module, '20' the module said the controller was silent),
    `ex_timestamp`. The controller's log gets a system event naming the
    command, the card and the number of attempts ("No answer came to ..." -
    whether the controller carried it out is not known). Routine upkeep
    (`ROUTINE_COMMANDS`: D7, B3) gets its event once, when the controller
    stops answering (`_controller_was_answering`), not at every failure after
    it. The event is written inside a savepoint: a failure to write it is
    logged and never keeps the command open. A `single_attempt` command that
    is not upkeep (a door opened or closed from the screen, an answer to a
    card) says instead that it is not sent again, because it was meant for
    that moment.
- **`_meant_for_the_moment(self)`**
  - `single_attempt` and not routine upkeep. Such a command that Odoo could
    not hand straight to a module it reaches (`_not_delivered_directly`,
    `hr.rfid.ctrl._base_command`) is closed at once instead of waiting for
    the module's next report; upkeep still waits.
- **`_controller_was_answering(self)`**
  - True unless the controller's previous finished command was closed for no
    answer ('30' or '20'); True when there is none before.

### Replies and reports (`controllers/main.py`, `models/hr_rfid_webstack.py`)

- **The shape of the reply** is settled per request by `_decode_post` and kept on the request (`request.rfid_reply_shape`: `json_rpc`, `id`, `plain`), never on the controller object, which is shared by every request. `_make_response` reads it: JSON-RPC envelope, plain JSON for a 100.1 (serial starting with '4'), and for a 10.3 an empty body or `{"cmd": {...}}` and nothing else - no `status`, no `ws` block.
- **One command out at a time** (`check_for_unsent_cmd`): while ANY command in `Process` is still awaited nothing is handed over and none is re-sent; once all are overdue, those that may not be sent again are closed (`_close_unanswered`), the oldest of the rest is re-sent (`retries + 1`), and with none left the next waiting one goes out in the same reply.
- **What the module answers to a command** (`parse_response`): `e=20` (controller silent) in the reply to a report re-sends the command in place (`_retry_command`) or closes it with '20'; on a delivery of its own (`direct_cmd=True`: the real-time channel, a module Odoo reaches) it goes back to `Wait` with `retries + 1` or is closed, because no reply carries a command there. `e=24` (module full) puts the command back to `Wait`. Neither re-queues a `single_attempt` command: it is closed.
- **On reconnect** (`_ws_on_connect_sync`): a `Process` command that may not be sent again is closed if its time is up, and holds the slot if it is still awaited; so does a command the module took in the reply to a report (`sent_on_channel` False) while it is still awaited - it has no id the module knows, and published now it would be carried out a second time. Otherwise the oldest `Process` command is published again (one of the channel is recognised by the module by its id), else the next waiting one.
- **A controller that has not described itself** (`_hw_description_is_on_its_way`): a card event for a controller with no `hw_version` is answered 400 while its F0 is `Wait`/`Process` (asked here if it never was), with a system event that keeps the report. After an F0 that ended without describing it, the event is noted ("Could not find a reader with that id") and accepted, so the module is not held back.
- **`_reply_with_command(command, status_code)`** - used by the reports that are answered with a command of their own (event 30 the clock, event 25/31 the status reading, an unknown controller its F0): the command goes out in the reply only when nothing else is out; otherwise it waits its turn.
- **`single_attempt`** commands are never re-sent: the answer to event 64 (DB, and DB2 for vending credit) and routine upkeep.
- **The answer to event 64** (a controller in external database mode asks about a card it does not keep) follows the same rights Odoo writes to the controllers that keep their cards (`hr.rfid.card._doors_it_opens_now`): the card is valid now (`card_ready`) and of the door's card type; the owner's place in the access group has started, has not expired and has visits left; the doors of inherited groups count; and the door's time schedule in that group covers the controller's local time (server time plus the module's time zone, `hr.rfid.time.schedule._lets_in_at`: Monday-first weekday rows, the last minute of a period included, schedule 0 at any time, 00:00-00:00 unused, holiday row not read). A group whose minimum time between passes is not over opens nothing - the member's group and, for an inherited door, the group the door comes from. A relay controller opens only the doors the card opens now.
- **Visits through an inherited door** count on the membership that gave the door (`filter_by_door` reads `all_door_ids`): a day pass whose group includes the gym is used up at the gym door.
- **The working time editor** numbers a day's periods 1-4 and keeps every minute on save (whole minutes, rounded; the 4th period's end is read in full).
- **A report that fails here** is recorded as a system event with the traceback AND the raw report (`with_context(keep_report=True)` bypasses the "save communications" setting, up to `KEPT_REPORT_MAX_CHARS` = 20000): a 10.3 reads an empty reply as "accepted" and forgets the event, so this record is its only copy. The kept copy leaves out the module's key (`_report_without_key`). Only for a module that has proved its key; before that the report is kept only if the site keeps its communication. The work on the report runs inside a savepoint (`post_event`, and the vending override): a failure undoes what was half done, and the record can still be written after a database error. The real-time channel does the same per event (`_ws_on_event_batch`).
- **A report with no key** is refused like a wrong key (400, "Webstack key and key in json did not match"); it used to raise.
- **Events 27/28** (alarm zone delay) are logged and acknowledged; they used to raise.
- **A late passage** (`hr.rfid.zone._passage_is_overtaken`): a granted passage more than `LATE_PASSAGE_AFTER_MINUTES` (10) old on arrival, with a newer one of the same person through a door of the zone, does not change the zone's people or the anti-passback flags; it is still recorded and still counts for attendance by its own time. A "newer" passage stamped after the server's own time is not counted (a controller with its clock ahead), and a passage that is not late always moves the zone. Each skip is logged at INFO with both passages.
- **Vending without a server for it** (`_hw_vending_request_for_balance`): logged as "the vending add-on is not installed here" and accepted. Reached only on a site without `hr_rfid_vending`: the add-on overrides `_hw_parse_event` and answers the reports of vending controllers itself, on the classic route and in real time alike.

### Cards and their schedules

- **`hr.rfid.access.group.door.rel._check_schedule_fits_the_controller()`**
  - Refuses a schedule above what the door's controller holds for a card: `hr.rfid.ctrl._card_schedule_max()` from `controllers/polimex.py` `CARD_SCHEDULE_MAX` (protocol D47: iCON130/iCON180/hotel 0-3, iCON110/iCON115/turnstile 0-15, others no known limit). The controller would otherwise refuse the whole card write (e=4). A controller that refuses a card anyway is explained in its system events by `hr.rfid.command._explain_a_refused_card_schedule()` (D1 with error 4 and a schedule above the limit).
- **`hr.rfid.card.door.rel.get_ts_code_string()`**
  - The card's schedule for each of the four readers, every reader of the door included. The card write itself does not read it: `hr.rfid.command.add_card` sends one D1 per reader, merged per slot by `hr.rfid.ctrl.add_remove_card`.
- **`hr.rfid.card._number_as_kept(number, card_type)`**
  - The number in the form the card stores it, or a refusal, applied in
    `create` and `write` BEFORE the ORM takes the value. The `number` field
    has `size=10` and the ORM cuts a longer value to fit (Char.convert_to_cache),
    so no constraint ever saw a number that was too long: the card was saved
    under its first 10 characters. Calls the card type's
    `check_and_fix_card_numer` (leading zeros; a number plate without its
    separators) and raises when the result is longer than the field.

### Searching the user events by name (`hr.rfid.event.user`)

- **`_search_name(self, operator, value)`** - the search method of the computed,
  unstored `name` (first field of the events' search view and part of
  `_rec_names_search`, so also the name search of an event link): `like` /
  `ilike` become an OR over `employee_id.name`, `contact_id.name`,
  `door_id.name` and the `event_action` keys whose label, in the searcher's
  language, contains the text (`_search_name_actions`); `in` (what `=` and
  "is set" arrive as) reads each exact name back into action, owner and door
  (`_search_name_equal`), and `False` matches nothing because every name
  holds the action; a negative operator returns `NotImplemented` and the ORM
  negates the positive search. `hr.rfid.vending.event` inherits it and
  overrides `_search_name_containing` / `_search_name_equal` for sales, whose
  name is "product - buyer". Without it every text search in that box raised "Cannot convert
  hr.rfid.event.user.name to SQL because it is not stored" (client case,
  10.11.2026).

## The words for a machine's problem

- **`_vending_problem_text(self, event_n, data)`** - decorators: -
  - The words for a machine's event 48 or 49, written as the system event by the event controller. From the vending part of the FA event (protocol D48): product `data[4:6]`, code of 48 `data[6:8]`. 49 = credit returned (product 0 = nothing chosen); 48 = the firmware's code (16: 0, 1, 2, 4, 5; 20: 0, 2, 4, 5; 21: 0, 1, 2, 3, 4, 6, 7). Unknown codes and data too short to read are shown as they came.

## How a sale is named and found (`hr.rfid.vending.event`)

- **`_compute_user_ev_name(self)`** - decorators: `@api.depends('item_sold_id.name')`
  (added to the dependencies of `hr.rfid.event.user`). A sale (`47`) reads
  "product - buyer" (either part alone when the other is missing, the
  action's label when both are); every other event is computed by
  `hr_rfid` as an access event. The sales are taken out of the set before
  `super()`, so a name never depends on the other events computed with it.
  - calls `super() `_compute_user_ev_name``
- **`_search_name_containing(self, operator, value)`** - a sale is matched
  by `item_sold_id.name` and `employee_id.name` (and, with neither, by the
  sale's action label through `_search_name_actions`); every other event by
  `hr_rfid`'s rule. Makes the first option of the vending events' search
  box find a product's sales.
  - calls `super() `_search_name_containing``
- **`_search_name_equal(self, name)`** - the exact name of a sale read back
  into product and buyer, trying every " - " as the boundary (either name may
  hold it).
  - calls `super() `_search_name_equal``

## Where the add-on answers a vending controller

- **`hr.rfid.webstack._hw_parse_event(self, post_data)`** - `models/hr_rfid_webstack.py`.
  The add-on answers the reports of a vending controller where every report of
  a module is read, before the core does, so the answer is the same over the
  classic route (`/hr/rfid/event`), the real-time connection and the demo.
  There is no route of the add-on's own any more: the module's key, the
  savepoint around the work and the record of a failed report are the core
  route's.
  - `_hw_vending_event(controller, post_data)` - the reply, or `None` for a
    report that is not vending's (the core reads it)
  - `_hw_vending_credit_request` (event 64: `DB2` with the balance,
    `single_attempt`), `_hw_vending_sale` (47), `_hw_vending_cash_on_card`
    (50); events 48 and 49 become system events

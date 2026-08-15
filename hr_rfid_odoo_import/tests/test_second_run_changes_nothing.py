# -*- coding: utf-8 -*-
"""Running the transfer again must not produce a second copy of anything.

The owner's acceptance criterion, in his words: "The import must be runnable
an unlimited number of times and must never duplicate data."

Nothing proved that. The nearest test drives ONE bulk helper on ONE model with
one column; it never runs a phase, let alone the chain, and it never touches
the ORM path - which is where the relations and the child records are made.
Those are the rows that duplicate silently, because nobody asks for them: a
card-to-door permission, an access-group membership, the credential record that
comes into being underneath a module. A duplicate there is not visible in any
count the operator reads; it is visible at the door.

So this runs the WHOLE chain of phases, in the order the wizard runs it, three
times over one and the same source, and counts the rows of every model the
phases touch - the entities, the relations, the children, and the external-ID
external ID itself - before and after.

The other system is answered from a dict rather than over the network. Only the
reading side is stood in for: every write is the real one, through the real
model layer, with the module's own side effects firing, so what is counted is
what a customer would end up with.
"""

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.base_importer import BaseImporter
from ..models.importers.phase import phase_plan

SOURCE_DB = "second_run_src"

#: The one company in the fixture, as the other system numbers it.
SOURCE_COMPANY = 101

#: Source record ids. Spelt out so a failure message names a real record.
CARD_TYPE = 1
CATEGORY = 2
DEPARTMENT = 10
TIME_SCHEDULE = 20
WEBSTACK = 30
CONTROLLER = 40
DOOR = 50
READER = 60
ACCESS_GROUP = 70
AG_DOOR_REL = 80
PARTNER = 90
EMPLOYEE = 100
AG_EMPLOYEE_REL = 110
AG_CONTACT_REL = 120
EMPLOYEE_CARD = 130
CONTACT_CARD = 131
USER_EVENT = 140
SYSTEM_EVENT = 150
ATTENDANCE = 160

DOOR_NAME_IN_THE_SOURCE = "Front gate"
ACCESS_GROUP_NAME_IN_THE_SOURCE = "Gate crew"

#: What the operator ticked. Everything the fixture carries is asked for.
OPTIONS = {
    "import_hardware": True,
    "import_people": True,
    "import_all_partners": True,
    "import_all_employees": True,
    "import_users": False,
    "import_images": False,
    "import_access": True,
    "import_sites": True,
    "import_cameras": True,
    "import_user_events": True,
    "import_system_events": True,
    "import_th_logs": False,
    "import_attendance": True,
    "import_attendance_extra": False,
    "import_vending": False,
    "import_service": False,
}

#: What the other system has installed. The phases themselves decide which of
#: them can run here - that gate is the module's own (``phase_plan``).
SOURCE_MODULES = {
    "hr_rfid",
    "hr_attendance_multi_rfid",
    "hr_rfid_site_manager",
    "polimex_ip_cam",
}

#: The things a customer would name: modules, controllers, doors, people, cards.
ENTITY_MODELS = (
    "hr.rfid.card.type",
    "hr.employee.category",
    "hr.department",
    "hr.rfid.time.schedule",
    "hr.rfid.webstack",
    "hr.rfid.ctrl",
    "hr.rfid.door",
    "hr.rfid.reader",
    "hr.rfid.access.group",
    "res.partner",
    "hr.employee",
    "hr.rfid.card",
)

#: The half that duplicates without anyone asking for it. Nobody imports a
#: card-to-door permission; it comes into being when the card arrives. The same
#: goes for the credential record underneath a module.
RELATION_MODELS = (
    "hr.rfid.access.group.door.rel",
    "hr.rfid.access.group.employee.rel",
    "hr.rfid.access.group.contact.rel",
    "hr.rfid.card.door.rel",
)

#: Written straight to the table, past the model layer, for speed.
HISTORY_MODELS = (
    "hr.rfid.event.user",
    "hr.rfid.event.system",
    "hr.attendance",
)

#: Counted only where this system can hold them at all.
MODELS_IF_PRESENT = (
    "hr.rfid.site",
    "cctv.camera",
    "cctv.camera.rfid.rel",
    "polimex.ws.endpoint",
    "hr.rfid.command",
)


def _plain(value):
    """A source value as an id: ``[7, 'Name']`` and ``7`` are the same thing."""
    if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], int):
        return value[0]
    return value


def _leaf_matches(record, field, operator, wanted):
    have = _plain(record.get(field, False))
    if operator in ("in", "not in"):
        # The right-hand side is a LIST of ids here. Running it through
        # _plain would turn a two-element list into its first element and
        # silently halve the set that was asked for.
        allowed = [_plain(value) for value in wanted]
        return (have in allowed) if operator == "in" else (have not in allowed)
    wanted = _plain(wanted)
    if operator == "=":
        return have == wanted
    if operator == "!=":
        return have != wanted
    if operator in (">", ">=", "<", "<="):
        if have is False or wanted is False:
            return False
        return {
            ">": have > wanted,
            ">=": have >= wanted,
            "<": have < wanted,
            "<=": have <= wanted,
        }[operator]
    # An operator the stand-in does not model: hand the record over rather
    # than invent a filter, so a phase is never fed less than it asked for.
    return True


def _matches(record, domain):
    """Whether one source record satisfies the plain leaves of a domain.

    Chained leaves (``controller_id.webstack_id.company_id``) and the prefix
    operators are passed over deliberately: the fixture holds a single company,
    so a scope expressed through a chain covers everything in it. Plain leaves
    are NOT passed over - the phases use them to ask for a subset, and a
    stand-in that hands over more than was asked for would be testing the
    importer against data it could never receive.
    """
    for leaf in domain:
        if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
            continue
        field, operator, wanted = leaf
        if "." in field:
            continue
        if not _leaf_matches(record, field, operator, wanted):
            return False
    return True


class _StubbedSource(BaseImporter):
    """The other system, answered from a dict instead of over the network.

    Every method that would reach for XML-RPC is answered here and nothing
    else is replaced, so the whole receiving side - the ORM writes, the
    module's own side effects, the external-ID external ID - is the real one.
    """

    def __init__(self, env, data, company_map, options):
        super().__init__(
            env=env,
            source_url="http://localhost:1",
            source_db=SOURCE_DB,
            source_uid=1,
            source_password="x",
            company_map=company_map,
            options=options,
        )
        self._data = data

    def _has_model(self, model):
        return model in self._data

    def _get_source_fields(self, model):
        names = set()
        for record in self._data.get(model, ()):
            names |= set(record)
        return {name: {"store": True} for name in names}

    def _has_field(self, model, field_name):
        return field_name in self._get_source_fields(model)

    def _can_read_fields(self, model, fields):
        return True

    def _search_read(self, model, domain, fields, order="id asc", limit=0,
                     include_archived=True):
        wanted = set(fields or ()) | {"id"}
        rows = [
            {k: v for k, v in record.items() if k in wanted}
            for record in self._data.get(model, ())
            if _matches(record, domain)
        ]
        rows.sort(key=lambda row: row["id"])
        return rows[:limit] if limit else rows

    def _search_count(self, model, domain):
        return len(self._search_read(model, domain, ["id"]))


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_rerun")
class TestSecondRunChangesNothing(TransactionCase):
    """The transfer may be run again, and again, without copying anything twice.

    * ``test_the_first_run_brings_the_data_over`` proves the fixture actually
      exercises the chain. Without it every assertion below would pass just as
      happily against a transfer that did nothing at all.
    * ``test_a_second_run_creates_nothing_new`` and
      ``test_a_third_run_still_creates_nothing`` are the owner's criterion:
      run it as often as you like, the data does not multiply.
    * ``test_a_second_run_does_not_rebuild_the_permissions`` watches the half
      nobody asks for - the memberships and the card-to-door permissions - and
      compares the rows themselves, not their number, so a quiet
      delete-and-recreate is caught as well as a duplicate.
    * ``test_a_door_renamed_here_goes_back_to_the_other_systems_name`` and
      ``test_a_person_renamed_here_keeps_the_correction`` state what a second
      run DOES do to a record someone edited here in the meantime - and they
      say it separately, because the answer is not the same for both. The
      equipment and the cards are written again from the other system; people,
      contacts, departments and access groups are recognised and left alone.
      That pair is what the confirm page promises the operator, so it is proved
      here rather than assumed.
    * ``test_a_record_edited_here_keeps_its_identity_after_a_second_run`` proves
      that whatever a second run does to the contents, it is still the SAME
      record - not a second one beside it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company_map = {SOURCE_COMPANY: cls.company.id}
        cls.source = cls._build_source()
        cls.counted_models = (
            ENTITY_MODELS
            + RELATION_MODELS
            + HISTORY_MODELS
            + tuple(m for m in MODELS_IF_PRESENT if m in cls.env)
        )

    # ── the other system's contents ──────────────────────────

    @classmethod
    def _build_source(cls):
        company = [SOURCE_COMPANY, cls.company.name]
        return {
            # Card types ship with the modules on both sides and carry the same
            # external id there, so the transfer matches rather than copies.
            "ir.model.data": [{
                "id": 900,
                "module": "hr_rfid",
                "name": "hr_rfid_card_type_def",
                "model": "hr.rfid.card.type",
                "res_id": CARD_TYPE,
            }],
            "hr.rfid.card.type": [{"id": CARD_TYPE, "name": "Standard card"}],
            "hr.employee.category": [
                {"id": CATEGORY, "name": "Imported staff", "color": 3},
            ],
            "hr.department": [{
                "id": DEPARTMENT,
                "name": "Gatehouse",
                "company_id": company,
                "parent_id": False,
                "color": 0,
                "note": False,
                "hr_rfid_default_access_group": [ACCESS_GROUP, "Gate crew"],
                "hr_rfid_allowed_access_groups": [ACCESS_GROUP],
            }],
            "hr.rfid.time.schedule": [{
                "id": TIME_SCHEDULE,
                "name": "Round the clock",
                "number": 1,
                "company_id": company,
                "ts_data": False,
            }],
            "hr.rfid.webstack": [{
                "id": WEBSTACK,
                "name": "Gate module",
                "serial": "990001",
                "key": "0000",
                "company_id": company,
                "active": True,
                "behind_nat": True,
                "available": "u",
            }],
            "hr.rfid.ctrl": [{
                "id": CONTROLLER,
                "name": "Gate controller",
                "ctrl_id": 1,
                "webstack_id": [WEBSTACK, "Gate module"],
            }],
            "hr.rfid.door": [{
                "id": DOOR,
                "name": DOOR_NAME_IN_THE_SOURCE,
                "number": 1,
                "controller_id": [CONTROLLER, "Gate controller"],
                "card_type": [CARD_TYPE, "Standard card"],
            }],
            "hr.rfid.reader": [{
                "id": READER,
                "name": "Gate reader",
                "number": 1,
                "controller_id": [CONTROLLER, "Gate controller"],
                "reader_type": "0",
                "door_ids": [DOOR],
            }],
            "hr.rfid.access.group": [{
                "id": ACCESS_GROUP,
                "name": ACCESS_GROUP_NAME_IN_THE_SOURCE,
                "company_id": company,
                "inherited_ids": [],
                "department_ids": [DEPARTMENT],
            }],
            "hr.rfid.access.group.door.rel": [{
                "id": AG_DOOR_REL,
                "access_group_id": [ACCESS_GROUP, "Gate crew"],
                "door_id": [DOOR, DOOR_NAME_IN_THE_SOURCE],
                "time_schedule_id": [TIME_SCHEDULE, "Round the clock"],
                "alarm_rights": False,
            }],
            "res.partner": [{
                "id": PARTNER,
                "name": "Visiting contractor",
                "company_id": company,
                "active": True,
                "parent_id": False,
            }],
            "hr.employee": [{
                "id": EMPLOYEE,
                "name": "Gate guard",
                "company_id": company,
                "active": True,
                "department_id": [DEPARTMENT, "Gatehouse"],
            }],
            "hr.rfid.access.group.employee.rel": [{
                "id": AG_EMPLOYEE_REL,
                "access_group_id": [ACCESS_GROUP, "Gate crew"],
                "employee_id": [EMPLOYEE, "Gate guard"],
                "state": True,
                "internal_state": True,
            }],
            "hr.rfid.access.group.contact.rel": [{
                "id": AG_CONTACT_REL,
                "access_group_id": [ACCESS_GROUP, "Gate crew"],
                "contact_id": [PARTNER, "Visiting contractor"],
                "state": True,
                "internal_state": True,
            }],
            "hr.rfid.card": [
                {
                    "id": EMPLOYEE_CARD,
                    "number": "0000100001",
                    "company_id": company,
                    "active": True,
                    "card_type": [CARD_TYPE, "Standard card"],
                    "employee_id": [EMPLOYEE, "Gate guard"],
                },
                {
                    "id": CONTACT_CARD,
                    "number": "0000100002",
                    "company_id": company,
                    "active": True,
                    "card_type": [CARD_TYPE, "Standard card"],
                    "contact_id": [PARTNER, "Visiting contractor"],
                },
            ],
            "hr.rfid.event.user": [{
                "id": USER_EVENT,
                "event_time": "2026-01-02 08:00:00",
                "event_action": "1",
                "door_id": [DOOR, DOOR_NAME_IN_THE_SOURCE],
                "reader_id": [READER, "Gate reader"],
                "card_id": [EMPLOYEE_CARD, "0000100001"],
                "employee_id": [EMPLOYEE, "Gate guard"],
            }],
            "hr.rfid.event.system": [{
                "id": SYSTEM_EVENT,
                "timestamp": "2026-01-02 08:05:00",
                "webstack_id": [WEBSTACK, "Gate module"],
                "event_action": "30",
            }],
            "hr.attendance": [{
                "id": ATTENDANCE,
                "employee_id": [EMPLOYEE, "Gate guard"],
                "check_in": "2026-01-02 08:00:00",
                "check_out": "2026-01-02 17:00:00",
            }],
            # Present on the other system, empty here: the phases must run and
            # come back with nothing rather than be skipped.
            "hr.rfid.site": [],
            "cctv.camera": [],
            "cctv.camera.rfid.rel": [],
        }

    # ── driving the transfer ─────────────────────────────────

    def _run_the_transfer(self):
        """One complete pass, exactly as the wizard drives it.

        A pass gets a NEW reader, with the in-memory source-to-target map
        empty. That is the honest shape of a second run: it happens in another
        process - the next cron cycle, another worker - and everything it needs
        to recognise has to come back from the external-ID external ID.

        Every step reports what became of it, and those reports are read here
        on EVERY pass. A phase does not stop at a step that breaks: it records
        the failure and carries on, which is right - one refused model must not
        take the rest of the transfer down. But a pass in which every step broke
        also creates nothing, which is exactly what a correct second pass looks
        like. Read the reports and the two are told apart; ignore them, and the
        checks below would go green over a transfer that failed from end to end.
        """
        source = _StubbedSource(self.env, self.source, self.company_map, OPTIONS)
        ran = []
        broken = []
        for phase, skipped_because in phase_plan(self.env, OPTIONS, SOURCE_MODULES):
            if skipped_because:
                continue
            results = phase(source).run(None) or []
            broken += [
                "%s / %s: %s" % (phase.NAME, result.get("model", "?"),
                                 result.get("error", ""))
                for result in results
                if result.get("status") == "error"
            ]
            ran.append(phase.NAME)
        self.env.flush_all()
        self.assertTrue(
            ran, "no phase ran at all - the test would prove nothing")
        self.assertFalse(
            broken,
            "steps of this pass could not be carried out, so anything it did "
            "not create proves nothing: %s" % "; ".join(broken),
        )
        return source

    # ── counting ─────────────────────────────────────────────

    def _snapshot(self):
        """Which rows exist right now, per model."""
        return {
            model: set(
                self.env[model].sudo().with_context(active_test=False)
                .search([]).ids
            )
            for model in self.counted_models
        }

    def _ledger_size(self, source):
        """How many external IDs this transfer has written."""
        module, _dot, name = source._xml_id("probe", 0).partition(".")
        prefix = name.rsplit("probe_0", 1)[0]
        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_data WHERE module = %s AND name LIKE %s",
            (module, prefix + "%"),
        )
        return self.env.cr.fetchone()[0]

    def _appeared(self, before, after):
        """{model: rows that were not there before}, empty models left out."""
        return {
            model: sorted(after[model] - before[model])
            for model in after
            if after[model] - before[model]
        }

    def _record(self, model, source_id, source):
        """The target record a source record was transferred into."""
        xid = source._xml_id(model.replace(".", "_"), source_id)
        module, _dot, name = xid.partition(".")
        entry = self.env["ir.model.data"].sudo().search(
            [("module", "=", module), ("name", "=", name), ("model", "=", model)],
            limit=1,
        )
        Model = self.env[model].sudo().with_context(active_test=False)
        return Model.browse(entry.res_id).exists() if entry else Model.browse()

    # ── the fixture really does exercise the chain ───────────

    def test_the_first_run_brings_the_data_over(self):
        """Everything below is worthless if the transfer moves nothing.

        A count that does not change between two runs is exactly what a
        transfer that never worked also produces. So this names, one by one,
        the kinds of record a customer would expect to find afterwards - and
        goes red the day the chain stops producing one of them, instead of
        letting the idempotency checks pass on an empty target.
        """
        before = self._snapshot()
        source = self._run_the_transfer()
        appeared = self._appeared(before, self._snapshot())

        expected = [
            "hr.department",
            "hr.employee.category",
            "hr.rfid.time.schedule",
            "hr.rfid.webstack",
            "hr.rfid.ctrl",
            "hr.rfid.door",
            "hr.rfid.reader",
            "hr.rfid.access.group",
            "hr.rfid.access.group.door.rel",
            "hr.rfid.access.group.employee.rel",
            "hr.rfid.access.group.contact.rel",
            "hr.rfid.card",
            "hr.rfid.card.door.rel",
            "res.partner",
            "hr.employee",
            "hr.rfid.event.user",
            "hr.rfid.event.system",
            "hr.attendance",
        ]
        missing = [model for model in expected if model not in appeared]
        self.assertFalse(
            missing,
            "the transfer produced nothing of these kinds, so the re-run "
            "checks would be measuring an empty target: %s" % ", ".join(missing),
        )
        # The card type ships with the modules on both sides: it is matched to
        # the one already here, never copied.
        self.assertNotIn(
            "hr.rfid.card.type", appeared,
            "a card type that ships with the modules must be matched, not "
            "copied - a second one is not the type the doors refer to")
        self.assertTrue(self._ledger_size(source))

    # ── the owner's criterion ────────────────────────────────

    def test_a_second_run_creates_nothing_new(self):
        """The owner's words: runnable any number of times, never duplicates.

        Every model the phases touch is counted - the entities, the relations,
        the records that come into being underneath them, and the history
        written straight to the tables.
        """
        self._run_the_transfer()
        after_first = self._snapshot()

        self._run_the_transfer()
        duplicated = self._appeared(after_first, self._snapshot())

        self.assertEqual(
            duplicated, {},
            "a second run of the same transfer produced records that were not "
            "there after the first one: %s" % duplicated,
        )

    def test_a_third_run_still_creates_nothing(self):
        """An unlimited number of runs means the third one as well.

        A guard that only remembers the previous pass would let the count creep
        up one row per run - slowly enough that nobody connects it to the
        transfer.
        """
        self._run_the_transfer()
        self._run_the_transfer()
        after_second = self._snapshot()

        self._run_the_transfer()
        duplicated = self._appeared(after_second, self._snapshot())

        self.assertEqual(
            duplicated, {},
            "the transfer stops being repeatable after the second run: %s"
            % duplicated,
        )

    def test_a_second_run_does_not_rebuild_the_permissions(self):
        """The half nobody asks for must come out of a re-run untouched.

        Nobody transfers a card-to-door permission; it appears because the card
        appeared. Counting is not enough here: a pass that quietly deletes the
        permissions and builds them again keeps the count identical, loses the
        history hanging off them, and - on a live site - takes the rights away
        from the doors for as long as the pass runs.
        """
        self._run_the_transfer()
        after_first = {
            model: rows for model, rows in self._snapshot().items()
            if model in RELATION_MODELS
        }
        self.assertTrue(
            any(after_first.values()),
            "no membership and no door permission was produced at all - this "
            "check would pass on an empty target")

        self._run_the_transfer()
        after_second = {
            model: rows for model, rows in self._snapshot().items()
            if model in RELATION_MODELS
        }

        for model in RELATION_MODELS:
            self.assertEqual(
                after_second[model], after_first[model],
                "%s came out of the second run as different rows - they were "
                "either duplicated or thrown away and made again" % model,
            )

    # ── what a second run does to a record edited here ───────

    def test_a_door_renamed_here_goes_back_to_the_other_systems_name(self):
        """The equipment and the cards are put back to what the source holds.

        Decided by the owner: running the transfer again REFRESHES the doors,
        the cards, the modules and the controllers. So an operator's edit made
        in between is not preserved - it is replaced by the source's value. The
        confirm page promises exactly this, in these words: a card switched off
        here comes back on, a door renamed here gets its old name back. It is
        proved here so a change of mind shows up as a failing test rather than
        as a surprise at a customer.
        """
        first = self._run_the_transfer()
        door = self._record("hr.rfid.door", DOOR, first)
        self.assertTrue(door, "the door did not come across at all")
        self.assertEqual(door.name, DOOR_NAME_IN_THE_SOURCE)

        door.write({"name": "Renamed after the transfer"})

        self._run_the_transfer()
        self.assertEqual(
            door.name, DOOR_NAME_IN_THE_SOURCE,
            "a second run is meant to bring the equipment back into line with "
            "the other system",
        )

    def test_a_person_renamed_here_keeps_the_correction(self):
        """A person put right here is NOT overwritten by a later transfer.

        The other half of the promise, and the one that was being told wrongly:
        the confirm page used to say a repeat transfer puts everything back to
        the other system's version. It does not. People, contacts, departments
        and access groups are recognised by what the first transfer recorded and
        left exactly as they are - which is what makes it safe to correct a
        misspelt name here while transfers keep running. If that ever changes,
        a customer loses every correction they made, so it is stated as its own
        claim rather than hidden inside the refresh one.
        """
        first = self._run_the_transfer()
        person = self._record("hr.employee", EMPLOYEE, first)
        self.assertTrue(person, "the person did not come across at all")
        corrected = "Gate guard (corrected here)"
        person.write({"name": corrected})

        self._run_the_transfer()
        self.assertEqual(
            person.name, corrected,
            "a later transfer overwrote a correction made here - the confirm "
            "page promises the operator it will not",
        )

    def test_a_department_added_here_to_a_group_is_taken_out_again(self):
        """The third half of the promise: a list the source keeps is rebuilt.

        The confirm page tells the operator this in as many words, and it is
        the one of the three that costs them work if it is wrong: whoever
        widened an access group here has to do it again after every transfer,
        and nothing on screen says so.
        """
        first = self._run_the_transfer()
        group = self._record("hr.rfid.access.group", ACCESS_GROUP, first)
        self.assertTrue(group, "the access group did not come across at all")
        added_here = self.env["hr.department"].create({
            "name": "Added here after the transfer",
            "company_id": self.company.id,
        })
        group.write({"department_ids": [(4, added_here.id)]})
        self.assertIn(added_here, group.department_ids)

        self._run_the_transfer()
        self.assertNotIn(
            added_here, group.department_ids,
            "the confirm page promises the operator that a list is rebuilt "
            "from the other system - this one was left as it was",
        )

    def test_a_record_edited_here_keeps_its_identity_after_a_second_run(self):
        """Whatever a re-run does to the contents, it is the SAME record.

        This is the failure that costs a customer their site: a second run that
        does not recognise what it brought over the first time leaves the
        original in place and puts a second one beside it. The cards, the
        events and the permissions stay on the first; the operator works on the
        second; and both look perfectly normal on screen.
        """
        first = self._run_the_transfer()
        group = self._record("hr.rfid.access.group", ACCESS_GROUP, first)
        self.assertTrue(group, "the access group did not come across at all")
        original_id = group.id
        group.write({"name": "Renamed after the transfer"})

        second = self._run_the_transfer()
        again = self._record("hr.rfid.access.group", ACCESS_GROUP, second)

        self.assertEqual(
            again.id, original_id,
            "the second run no longer recognises the access group it brought "
            "over itself",
        )
        self.assertEqual(
            self.env["hr.rfid.access.group"].sudo().with_context(
                active_test=False,
            ).search_count([("id", "in", [original_id, again.id])]),
            1,
            "there is now more than one access group for one source group",
        )

    def test_the_external_id_ledger_does_not_grow_on_a_second_run(self):
        """The external ID is the map from the other system to this one.

        A second entry for one source record means the map answers with
        whichever row happens to be found first, so the next pass attaches the
        cards and the events to a different record than the last one did.
        """
        first = self._run_the_transfer()
        after_first = self._ledger_size(first)
        self.assertTrue(after_first, "nothing was recorded as transferred")

        second = self._run_the_transfer()
        self.assertEqual(
            self._ledger_size(second), after_first,
            "the second run wrote further entries for records that already "
            "had one",
        )

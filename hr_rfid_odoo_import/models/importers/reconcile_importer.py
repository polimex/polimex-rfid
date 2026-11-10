# -*- coding: utf-8 -*-
"""Phase 10: the transfer is checked against the OTHER SYSTEM, tenant by tenant.

Every earlier phase counts what IT moved, and Phase 9 checks that what is here
holds together. Neither of them asks the question the owner actually asks: does
this system now hold what the other one holds? A step can report a clean line
over data it never even looked for - that is exactly how 152 469 daily
working-time roll-ups stayed behind with nothing in the protocol to say so, and
how one tenant lost all 400 of its cards while every other line read fine.

So this phase asks the SOURCE for its numbers, per tenant, and compares them
with what carries this transfer's identity here. It is the audit that found
today's defects, moved inside the product where the operator can run it instead
of somebody having to write it again by hand.

Two rules make it trustworthy rather than reassuring:

* It counts on the SAME axis the transfer reads - archived records included.
  Counted the other way, the preview page promised 6 395 cards where 8 505 came
  across, and the operator compared the protocol against the wrong number.
* It says out loud when it CANNOT compare something (a model this version does
  not keep, a source that refuses the read). A comparison that did not happen
  reads exactly like a comparison that agreed, and silence is not agreement.

A difference is a problem only in what THIS transfer carried (owner's
decision, 10.11.2026). Every kind is still compared, but a kind left unticked
shows its numbers as a remark: a second transfer of the attendance alone
finished every step and was reported "stopped by a problem" over people,
events and daily summaries it was never asked to bring.
"""
import json
import logging
import time

from odoo.tools import LazyTranslate

from .phase import PhaseImporter

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

#: How many tenants are named in one protocol row before "+N more".
NAMED_TENANTS = 6

#: What the operator reads for each kind, in their language.
#: A mapping and not a field of the tuples below on purpose: core's term
#: extractor treats the "(" that opens the tuple after a ``_lt(...)`` call as
#: one more ``_lt(`` (odoo/tools/babel/python_extractor.py keeps the last
#: NAME it saw), and every model name of the list went out for translation.
KIND_LABELS = {
    'hr.rfid.webstack': _lt('communication modules'),
    'hr.rfid.ctrl': _lt('controllers'),
    'hr.rfid.door': _lt('doors'),
    'hr.rfid.reader': _lt('readers'),
    'hr.rfid.time.schedule': _lt('time schedules'),
    'hr.rfid.access.group': _lt('access groups'),
    'hr.rfid.access.group.door.rel': _lt('door permissions'),
    'hr.rfid.access.group.employee.rel': _lt('staff in access groups'),
    'hr.rfid.access.group.contact.rel': _lt('contacts in access groups'),
    'hr.rfid.card': _lt('cards'),
    'hr.employee': _lt('people'),
    'hr.department': _lt('departments'),
    'hr.rfid.zone': _lt('zones'),
    'hr.rfid.event.user': _lt('access events'),
    'hr.rfid.event.system': _lt('system events'),
    'hr.attendance': _lt('attendances'),
    'hr.attendance.extra': _lt('daily working-time summaries'),
    'hr.rfid.vending.balance.history': _lt('vending balance entries'),
    'hr.rfid.vending.event': _lt('vending sales'),
    'rfid.service.sale': _lt('service sales'),
    'hr.leave': _lt('absences'),
    'hr.leave.allocation': _lt('leave balances'),
}

CARRYABLE_LEAVE_STATES = ['confirm', 'validate1', 'validate']

#: What is reconciled, how each kind reaches a company, and what carries it.
#: (model, path to the company, the option of the transfer that carries it,
#: extra source domain)
#: The extra domain is what the transfer itself carries: absences that were
#: approved or are still in flight, and balances that were granted. Counted
#: without it, the refused and cancelled ones of the other system would be
#: reported as losses every single time - and a control that cries wolf is a
#: control nobody reads.
#:
#: The path is the business chain: a reader belongs to a controller, a
#: controller to a communication module, a module to a company; an attendance
#: to the person, a person to a company. '' means the model carries the company
#: itself.
#:
#: The option is the one the phase that brings the kind runs under (phase.py,
#: each importer's OPTION and the switches inside its run()); a tuple when
#: any of several ticks asks for the kind.
RECONCILED = [
    ('hr.rfid.webstack', '', 'import_hardware'),
    ('hr.rfid.ctrl', 'webstack_id', 'import_hardware'),
    ('hr.rfid.door', 'controller_id.webstack_id', 'import_hardware'),
    ('hr.rfid.reader', 'controller_id.webstack_id', 'import_hardware'),
    ('hr.rfid.time.schedule', '', 'import_hardware'),
    ('hr.rfid.access.group', '', 'import_access'),
    ('hr.rfid.access.group.door.rel', 'access_group_id', 'import_access'),
    ('hr.rfid.access.group.employee.rel', 'access_group_id', 'import_access'),
    ('hr.rfid.access.group.contact.rel', 'access_group_id', 'import_access'),
    # Cards come with Access (access_importer.py). "Import Cards" is still on
    # the screen though no step reads it any more; an operator who ticked it
    # asked for the cards, and their loss is not a remark.
    ('hr.rfid.card', '', ('import_access', 'import_cards')),
    ('hr.employee', '', 'import_people'),
    ('hr.department', '', 'import_hardware'),
    ('hr.rfid.zone', '', 'import_hardware'),
    ('hr.rfid.event.user', 'reader_id.controller_id.webstack_id', 'import_user_events'),
    ('hr.rfid.event.system', 'webstack_id', 'import_system_events'),
    ('hr.attendance', 'employee_id', 'import_attendance'),
    ('hr.attendance.extra', 'employee_id', 'import_attendance_extra'),
    ('hr.rfid.vending.balance.history', 'employee_id', 'import_vending'),
    ('hr.rfid.vending.event', 'reader_id.controller_id.webstack_id', 'import_vending'),
    ('rfid.service.sale', '', 'import_service'),
    ('hr.leave', 'employee_id', 'import_leaves',
     [('state', 'in', CARRYABLE_LEAVE_STATES)]),
    ('hr.leave.allocation', 'employee_id', 'import_leaves',
     [('state', '=', 'validate')]),
]

#: {model: option} - what carries each reconciled kind.
CARRIED_BY = {entry[0]: entry[2] for entry in RECONCILED}

#: Who a record of a kind belongs to, where the step that carries it leaves
#: the record behind when that owner is not here - read in each step:
#: access_importer (cards: the person, else the contact; the staff and contact
#: memberships), attendance_importer (stays, daily summaries), leave_importer,
#: vending_importer (balance entries). [(field, owner model)], in the order
#: the step tries them.
OWNED_BY = {
    'hr.rfid.access.group.employee.rel': [('employee_id', 'hr.employee')],
    'hr.rfid.access.group.contact.rel': [('contact_id', 'res.partner')],
    'hr.rfid.card': [('employee_id', 'hr.employee'),
                     ('contact_id', 'res.partner')],
    'hr.attendance': [('employee_id', 'hr.employee')],
    'hr.attendance.extra': [('employee_id', 'hr.employee')],
    'hr.rfid.vending.balance.history': [('employee_id', 'hr.employee')],
    'hr.leave': [('employee_id', 'hr.employee')],
    'hr.leave.allocation': [('employee_id', 'hr.employee')],
}

#: What carries an owner kind (both come with People, people_importer.py).
OWNER_CARRIED_BY = {'hr.employee': 'import_people', 'res.partner': 'import_people'}

#: What the operator calls an owner kind.
OWNER_LABELS = {
    'hr.employee': KIND_LABELS['hr.employee'],
    'res.partner': _lt('contacts'),
}


class ReconcileImporter(PhaseImporter):
    PHASE_ID = 'Phase 10'
    NAME = 'Reconciliation with the other system'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.rfid.webstack',)
    OPTION = ''
    WEIGHT = 1

    def __init__(self, base):
        super().__init__(base)
        #: {owner model: the other system's ids of it that are here, or None}
        self._owners_here = {}

    def run(self, wizard):
        for entry in RECONCILED:
            model, path = entry[:2]
            extra = list(entry[3]) if len(entry) > 3 else []
            label = self.env._(KIND_LABELS[model])
            start = time.time()
            try:
                self.results.append(
                    self._reconcile(model, path, label, start, extra))
            except Exception as exc:                            # noqa: BLE001
                # A check that cannot run is itself a finding - reported, never
                # swallowed, because its silence would read as agreement. It
                # stops the transfer only over a kind it was asked to bring.
                _logger.warning("Could not reconcile %s: %s", model, exc,
                                exc_info=True)
                self.results.append(self.b._make_result(
                    label, 0, 0, duration=time.time() - start,
                    status='error' if self._carried(model) else 'skipped',
                    error=self.env._(
                        "%(kind)s could not be checked against the other "
                        "system: %(problem)s", kind=label,
                        problem=str(exc)[:200]),
                ))
        return self.results

    # ── one kind of record ────────────────────────────────────

    def _ticked(self, option):
        """Whether the operator asked this transfer to bring what ``option`` carries.

        The operator's own tick, not only the switch the steps run under: for
        the kinds a module brings (attendance, vending, services) that switch
        is also off when this system cannot take the data, and such data,
        asked for and left behind, is this transfer's problem - not a remark.
        """
        options = self.b.options or {}
        return bool(options.get(option)
                    or (options.get('ticked') or {}).get(option))

    def _carried(self, model):
        """Whether this transfer was asked to bring that kind.

        A kind no option governs is always this transfer's business.
        """
        option = CARRIED_BY.get(model)
        if option is None:
            return True
        options = option if isinstance(option, tuple) else (option,)
        return any(self._ticked(name) for name in options)

    def _reconcile(self, model, path, label, start, extra=()):
        """One protocol line for one kind: its numbers there and here.

        A kind this transfer was not asked to bring is still compared, but a
        difference in it is a remark, not a problem.
        """
        carried = self._carried(model)
        if model not in self.env:
            return self.b._make_result(
                label, 0, 0, duration=time.time() - start, status='skipped',
                error=self.env._(
                    "%(kind)s: this system does not keep that kind of data, so "
                    "there was nothing to compare.", kind=label))
        if not self.b._has_model(model):
            return self.b._make_result(
                label, 0, 0, duration=time.time() - start, status='skipped',
                error=self.env._(
                    "%(kind)s: the other system does not keep that kind of "
                    "data.", kind=label))

        owners = [owner for _field, owner in OWNED_BY.get(model, [])
                  if not self._ticked(OWNER_CARRIED_BY[owner])] if carried else []
        #: (target company, there, held) by what was found for the tenant:
        #: fewer here, MORE here than over there, records whose owner is not
        #: here, could not be asked, came out larger than the gap.
        found = {'short': [], 'surplus': [], 'unplaced': [], 'untold': [],
                 'unaccountable': []}
        unplaced_total = source_total = arrived_total = kept_total = 0
        for source_company, target_company in sorted(
                (self.b.company_map or {}).items(),
                key=lambda pair: pair[0]):
            if not target_company:
                continue
            there = self._count_on_the_source(model, path, source_company,
                                              extra)
            if there is None:
                return self.b._make_result(
                    label, 0, 0, duration=time.time() - start,
                    status='skipped',
                    error=self.env._(
                        "%(kind)s: the other system cannot be asked about this "
                        "per company, so no comparison was made.", kind=label))
            here = self._count_that_arrived(model, path, source_company,
                                            target_company)
            kept = self._kept_here_on_purpose(model, target_company)
            held = here + kept
            source_total += there
            arrived_total += here
            kept_total += kept
            accounted = held
            if owners and held < there:
                finding, orphans = self._explained_by_owners(
                    model, path, source_company, extra, there - held)
                if finding:
                    found[finding].append((target_company, there, held))
                unplaced_total += orphans
                accounted += orphans
            if accounted < there:
                found['short'].append((target_company, there, held))
            elif held > there:
                found['surplus'].append((target_company, there, held))

        status, notes = self._verdict(label, carried, owners, found,
                                      unplaced_total)
        return self.b._make_result(
            label, source_total, arrived_total, linked_count=kept_total,
            duration=time.time() - start, status=status, error=' '.join(notes))

    def _explained_by_owners(self, model, path, source_company, extra, gap):
        """How much of a tenant's gap the records of owners not here explain.

        ``(finding, count)``: ``('unplaced', n)`` when ``n`` such records fill
        part or all of the gap; ``('untold', 0)`` when the other system would
        not say; ``('unaccountable', 0)`` when it names more than the gap;
        ``(None, 0)`` when there are none.
        """
        orphans = self._owned_by_owners_not_here(model, path, source_company,
                                                 extra)
        if orphans is None:
            return 'untold', 0
        if orphans > gap:
            # Records that never arrived cannot outnumber the gap: the two
            # counts do not describe the same records, so they explain nothing
            # and the loss stays a loss.
            return 'unaccountable', 0
        return ('unplaced', orphans) if orphans else (None, 0)

    def _verdict(self, label, carried, owners, found, unplaced_total):
        """The line's status and the sentences that explain it."""
        short, surplus = found['short'], found['surplus']
        unplaced, untold = found['unplaced'], found['untold']
        unaccountable = found['unaccountable']
        status, notes = 'done', []
        owner_names = ', '.join(self.env._(OWNER_LABELS[o]) for o in owners)
        if not carried:
            if short or surplus:
                # Said, because the numbers are worth knowing - but as what
                # they are: this transfer was not asked to bring that kind.
                status = 'skipped'
                notes.append(self.env._(
                    "%(kind)s: not part of this transfer, so the difference is "
                    "shown for comparison only - %(where)s.",
                    kind=label, where=self._name_them(short + surplus)))
        elif short:
            status = 'error'
            notes.append(self.env._(
                "%(kind)s: the other system holds more than arrived here - "
                "%(where)s. Look at the step that carries them: what these "
                "records point at is usually what is missing.",
                kind=label, where=self._name_them(short)))
        elif surplus:
            # More here than there is not a loss, and often not a defect at all
            # (this system computes some things for itself), but it must be
            # said: nobody should have to discover it from a report months on.
            status = 'partial'
            notes.append(self.env._(
                "%(kind)s: more records are here than the other system holds - "
                "%(where)s. Anything this system works out for itself lands "
                "here as well as what came across.",
                kind=label, where=self._name_them(surplus)))
        if unplaced:
            if status == 'done':
                status = 'partial'
            notes.append(self.env._(
                "%(kind)s: %(count)s record(s) of the other system belong to "
                "%(owners)s that are not in this system, and %(owners)s were "
                "not part of this transfer - %(where)s.",
                kind=label, count=unplaced_total, owners=owner_names,
                where=self._name_them(unplaced)))
        if untold:
            notes.append(self.env._(
                "%(kind)s: the other system did not say how many of these "
                "belong to %(owners)s that are not in this system, so all of "
                "the difference counts as missing - %(where)s.",
                kind=label, owners=owner_names, where=self._name_them(untold)))
        if unaccountable:
            notes.append(self.env._(
                "%(kind)s: the other system names more records of %(owners)s "
                "that are not in this system than are missing here, so the "
                "two do not add up and all of the difference counts as "
                "missing - %(where)s.",
                kind=label, owners=owner_names,
                where=self._name_them(unaccountable)))
        return status, notes

    # ── the two numbers ───────────────────────────────────────

    def _kept_here_on_purpose(self, model, target_company):
        """Records of that tenant the transfer left out because this system has its own.

        Only stays so far: one the same to the second is already here, and one
        that differs keeps the stay recorded here (the attendance step says
        which). Neither is a loss, and counting them as one would turn every
        transfer over a working system into a failed one. Counted by the
        transfer itself as it went, because nothing on the record links them.
        """
        if model != 'hr.attendance':
            return 0
        from .attendance_importer import DIFFERS_KEY, SAME_HERE_KEY
        verdicts = self._attendance_verdicts()
        same = sum(1 for company in (verdicts.get(SAME_HERE_KEY) or {}).values()
                   if company == target_company)
        differ = sum(1 for entry in (verdicts.get(DIFFERS_KEY) or {}).values()
                     if entry[1] == target_company)
        return same + differ

    def _attendance_verdicts(self):
        """What the attendance step decided, as far as this check can know it.

        This transfer's own when it carried attendance. Otherwise those of the
        latest earlier transfer of the same system that did: this check
        compares every kind whatever was ticked, and a later transfer of the
        cards alone read the stays an earlier one had kept here on purpose as
        a difference - a loss before differences in unticked kinds became
        remarks, and a false remark since.
        """
        from .attendance_importer import ATTENDANCE_CURSOR
        from .base_importer import normalise_source_slug
        if ATTENDANCE_CURSOR in self.b.step_totals:
            return self.b.step_totals[ATTENDANCE_CURSOR]
        runs = self.env['hr.rfid.odoo.import.run'].sudo().search_read(
            [], ['source_slug', 'source_db', 'step_totals_json'], order='id desc')
        for run in runs:
            if normalise_source_slug(run['source_slug'] or run['source_db']) != self.b.source_slug:
                continue
            verdicts = json.loads(run['step_totals_json'] or '{}').get(ATTENDANCE_CURSOR)
            if verdicts:
                return verdicts
        return {}

    def _count_on_the_source(self, model, path, source_company, extra=()):
        """How many the OTHER system holds for that tenant.

        ``None`` when it cannot be asked that way - said out loud by the caller
        rather than counted as zero.
        """
        field = '%s.company_id' % path if path else 'company_id'
        try:
            # The same counter the rest of the transfer uses, so archived
            # records are included exactly as the reads include them.
            return self.b._search_count(
                model, [(field, '=', source_company)] + list(extra))
        except Exception:                                       # noqa: BLE001
            _logger.warning(
                "The other system refuses to count %s by %s", model, field,
                exc_info=True)
            return None

    def _count_that_arrived(self, model, path, source_company, target_company):
        """How many of that tenant's records are HERE, by transfer identity.

        Identity, never a look-alike count: the rows are the ones this transfer
        recorded as brought over (``ir.model.data``), intersected with the
        tenant they belong to here. A plain count of the target would also
        include whatever this system made by itself and would hide a loss
        behind it.
        """
        Model = self.env[model].sudo().with_context(active_test=False)
        field = '%s.company_id' % path if path else 'company_id'
        brought = self._ids_brought_over(model)
        if not brought:
            return 0
        try:
            return Model.search_count([('id', 'in', brought),
                                       (field, '=', target_company)])
        except Exception:                                       # noqa: BLE001
            # A chain this version does not have - count them all for the
            # tenant instead of pretending none arrived.
            _logger.warning("Cannot count %s here by %s", model, field,
                            exc_info=True)
            return len(brought)

    def _owned_by_owners_not_here(self, model, path, source_company, extra):
        """How many of that tenant's records over there belong to an owner that
        is not here, of a kind this transfer did not carry. ``None`` when it
        cannot be told.

        An attendance of a person who is not in this system cannot be here:
        there is nobody to hang it from. When people are part of the transfer,
        their own line says who is missing and this stays a loss. When they
        are not, it is the people's difference said once more, and it is said
        as one: a second transfer of the attendance alone was stopped by a
        single stay of a person the other system has and this one does not.

        Owners are tried in the order the step tries them (OWNED_BY): a card
        is the person's, and only a card with no person is the contact's.
        """
        missing = 0
        before = []         # the owners a later one is tried after
        for field, owner in OWNED_BY.get(model, []):
            if not self._ticked(OWNER_CARRIED_BY[owner]):
                here = self._owners_here_of(owner)
                if here is None:
                    return None
                count = self._count_on_the_source(
                    model, path, source_company,
                    list(extra) + before
                    + [(field, '!=', False), (field, 'not in', here)])
                if count is None:
                    return None
                missing += count
            before.append((field, '=', False))
        return missing

    def _owners_here_of(self, owner):
        """The other system's ids of that owner kind still here, read once a phase."""
        if owner not in self._owners_here:
            self._owners_here[owner] = self._source_ids_here(owner)
        return self._owners_here[owner]

    def _identity_prefix(self, model):
        """How this transfer starts the identity name of a record of that model."""
        return self.b._xml_id_name(model.replace('.', '_'), '')

    def _ledger(self, model):
        """This transfer's identity rows for that model: [{'name', 'res_id'}].

        By the exact prefix the steps write (``_xml_id_name``), model included:
        the identity of one source alone is the start of another's when one
        name continues the other ("acme" and "acme_old"), and that other
        system's records were counted as this one's.
        """
        from .base_importer import EXTERNAL_ID_MODULE
        prefix = self._identity_prefix(model)
        return self.env['ir.model.data'].sudo().search_read(
            [('model', '=', model),
             ('module', '=', EXTERNAL_ID_MODULE),
             ('name', '=like', prefix.replace('_', r'\_') + '%')],
            ['name', 'res_id'])

    def _ids_brought_over(self, model):
        """Target ids this transfer recorded for that model, from its own name."""
        return [row['res_id'] for row in self._ledger(model)]

    def _source_ids_here(self, model):
        """The other system's ids of that kind that this system still holds.

        Read from the transfer's own identity - the source id ends the name -
        and only for records that still exist here (archived included): one
        deleted here since is exactly an owner that is not here. ``None`` when
        a name does not end in an id: an owner that IS here would then be
        taken for one that is not, and its records' loss for a remark.
        """
        prefix = self._identity_prefix(model)
        rows = self._ledger(model)
        alive = set(self.env[model].sudo().browse(
            [row['res_id'] for row in rows]).exists().ids)
        ids = set()
        for row in rows:
            tail = row['name'][len(prefix):]
            if not tail.isdigit():
                _logger.warning(
                    "Identity %s of %s does not end in the other system's id - "
                    "records of the people not here are not told apart",
                    row['name'], model)
                return None
            if row['res_id'] in alive:
                ids.add(int(tail))
        return sorted(ids)

    def _name_them(self, rows):
        Company = self.env['res.company'].sudo()
        shown = rows[:NAMED_TENANTS]
        text = '; '.join(
            self.env._("%(company)s: %(there)s there, %(here)s here",
                       company=Company.browse(company).display_name,
                       there=there, here=here)
            for company, there, here in shown)
        if len(rows) > len(shown):
            text += '; ' + self.env._("+%(count)s more tenant(s)",
                                      count=len(rows) - len(shown))
        return text

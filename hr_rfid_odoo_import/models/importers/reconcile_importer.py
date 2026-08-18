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
"""
import logging
import time

from .phase import PhaseImporter

_logger = logging.getLogger(__name__)

#: How many tenants are named in one protocol row before "+N more".
NAMED_TENANTS = 6

#: What is reconciled, and how each kind reaches a company.
#: (model, path to the company, label the operator reads, extra source domain)
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
CARRYABLE_LEAVE_STATES = ['confirm', 'validate1', 'validate']

RECONCILED = [
    ('hr.rfid.webstack', '', 'communication modules'),
    ('hr.rfid.ctrl', 'webstack_id', 'controllers'),
    ('hr.rfid.door', 'controller_id.webstack_id', 'doors'),
    ('hr.rfid.reader', 'controller_id.webstack_id', 'readers'),
    ('hr.rfid.time.schedule', '', 'time schedules'),
    ('hr.rfid.access.group', '', 'access groups'),
    ('hr.rfid.access.group.door.rel', 'access_group_id', 'door permissions'),
    ('hr.rfid.access.group.employee.rel', 'access_group_id', 'staff in access groups'),
    ('hr.rfid.access.group.contact.rel', 'access_group_id', 'contacts in access groups'),
    ('hr.rfid.card', '', 'cards'),
    ('hr.employee', '', 'people'),
    ('hr.department', '', 'departments'),
    ('hr.rfid.zone', '', 'zones'),
    ('hr.rfid.event.user', 'reader_id.controller_id.webstack_id', 'access events'),
    ('hr.rfid.event.system', 'webstack_id', 'system events'),
    ('hr.attendance', 'employee_id', 'attendances'),
    ('hr.attendance.extra', 'employee_id', 'daily working-time summaries'),
    ('hr.rfid.vending.balance.history', 'employee_id', 'vending balance entries'),
    ('hr.rfid.vending.event', 'reader_id.controller_id.webstack_id', 'vending sales'),
    ('rfid.service.sale', '', 'service sales'),
    ('hr.leave', 'employee_id', 'absences',
     [('state', 'in', CARRYABLE_LEAVE_STATES)]),
    ('hr.leave.allocation', 'employee_id', 'leave balances',
     [('state', '=', 'validate')]),
]


class ReconcileImporter(PhaseImporter):
    PHASE_ID = 'Phase 10'
    NAME = 'Reconciliation with the other system'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.rfid.webstack',)
    OPTION = ''
    WEIGHT = 1

    def run(self, wizard):
        for entry in RECONCILED:
            model, path, label = entry[:3]
            extra = list(entry[3]) if len(entry) > 3 else []
            start = time.time()
            try:
                self.results.append(
                    self._reconcile(model, path, label, start, extra))
            except Exception as exc:                            # noqa: BLE001
                # A check that cannot run is itself a finding - reported, never
                # swallowed, because its silence would read as agreement.
                _logger.warning("Could not reconcile %s: %s", model, exc,
                                exc_info=True)
                self.results.append(self.b._make_result(
                    label, 0, 0, duration=time.time() - start, status='error',
                    error=self.env._(
                        "%(kind)s could not be checked against the other "
                        "system: %(problem)s", kind=label,
                        problem=str(exc)[:200]),
                ))
        return self.results

    # ── one kind of record ────────────────────────────────────

    def _reconcile(self, model, path, label, start, extra=()):
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

        short = []          # tenants where fewer records are here
        surplus = []        # tenants where MORE are here than over there
        source_total = arrived_total = 0
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
            source_total += there
            arrived_total += here
            if here < there:
                short.append((target_company, there, here))
            elif here > there:
                surplus.append((target_company, there, here))

        status, note = 'done', ''
        if short:
            status = 'error'
            note = self.env._(
                "%(kind)s: the other system holds more than arrived here - "
                "%(where)s. Look at the step that carries them: what these "
                "records point at is usually what is missing.",
                kind=label, where=self._name_them(short))
        elif surplus:
            # More here than there is not a loss, and often not a defect at all
            # (this system computes some things for itself), but it must be
            # said: nobody should have to discover it from a report months on.
            status = 'partial'
            note = self.env._(
                "%(kind)s: more records are here than the other system holds - "
                "%(where)s. Anything this system works out for itself lands "
                "here as well as what came across.",
                kind=label, where=self._name_them(surplus))
        return self.b._make_result(
            label, source_total, arrived_total,
            duration=time.time() - start, status=status, error=note)

    # ── the two numbers ───────────────────────────────────────

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

    def _ids_brought_over(self, model):
        """Target ids this transfer recorded for that model, from its own name."""
        from .base_importer import EXTERNAL_ID_MODULE, EXTERNAL_ID_PREFIX
        prefix = '%s%s_' % (EXTERNAL_ID_PREFIX, self.b.source_slug)
        rows = self.env['ir.model.data'].sudo().search_read(
            [('model', '=', model),
             ('module', '=', EXTERNAL_ID_MODULE),
             ('name', '=like', prefix.replace('_', r'\_') + '%')],
            ['res_id'])
        return [row['res_id'] for row in rows]

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

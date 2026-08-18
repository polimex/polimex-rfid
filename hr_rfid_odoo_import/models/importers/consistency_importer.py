# -*- coding: utf-8 -*-
"""Phase 9: the target vouches for its own integrity, by name.

Every earlier phase counts what IT moved; nobody looked at the WHOLE at the
end. The gap this closes was found the expensive way: a transfer went green,
the cameras' readers arrived correctly linked, and live cars still went
unrecorded for hours - the one list the event handler reads had stayed
empty, and no number anywhere said so. A consistency check is the operator's
proof that the moved system can actually run, not just that rows arrived.

Every check here is an invariant the RUNNING modules rely on, not a schema
nicety - each row names the offenders, because a count without names sends
the operator hunting.
"""
import logging
import time

from .phase import PhaseImporter

_logger = logging.getLogger(__name__)

#: How many offending records are named in a protocol row before "+N more".
NAMED_OFFENDERS = 8


class ConsistencyImporter(PhaseImporter):
    PHASE_ID = 'Phase 9'
    NAME = 'Consistency check'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.rfid.webstack',)
    OPTION = ''
    WEIGHT = 1

    #: Checks whose finding can be a faithful copy of the other system rather
    #: than something this transfer did. Keyed by check, valued by the count
    #: of the SAME shape on the source: equal numbers mean the other system
    #: has it too, and calling that an error makes a correct transfer read as
    #: a broken one. Measured on the 27-tenant cloud: 3 controllers behind
    #: archived modules and 46 readers with no door - identical on both sides,
    #: reported here as two red lines that sent the operator hunting.
    def _same_shape_on_the_source(self, name):
        counters = {
            'controllers_behind_archived_module':
                self._source_controllers_behind_archived_module,
            'readers_without_door': self._source_readers_without_door,
        }
        counter = counters.get(name)
        if not counter:
            return None
        try:
            return counter()
        except Exception:                                      # noqa: BLE001
            _logger.warning(
                "Could not ask the other system about %s - the finding is "
                "reported as it stands", name, exc_info=True)
            return None

    def _source_controllers_behind_archived_module(self):
        archived = [rec['id'] for rec in self.b._search_read(
            'hr.rfid.webstack', [('active', '=', False)], ['id'])]
        if not archived:
            return 0
        return self.b._search_count(
            'hr.rfid.ctrl', [('webstack_id', 'in', archived)])

    def _source_readers_without_door(self):
        readers = self.b._search_read('hr.rfid.reader', [], ['door_id'])
        return sum(1 for rec in readers if not rec.get('door_id'))

    def run(self, wizard):
        checks = [
            (self.env._("Controllers hidden behind an archived module"),
             self._controllers_behind_archived_module),
            (self.env._("Doors attached to no equipment"),
             self._doors_off_the_chain),
            (self.env._("Doors that no reader serves"),
             self._doors_without_readers),
            (self.env._("Readers wired to nothing"),
             self._readers_without_owner),
            (self.env._("Readers without a door"),
             self._readers_without_door),
            (self.env._("Chains that cross companies"),
             self._chain_company_mismatch),
            (self.env._("Cards that belong to nobody"),
             self._cards_without_owner),
            (self.env._("Cards held by a person of another company"),
             self._cards_with_foreign_owner),
            (self.env._("Door permissions across companies"),
             self._door_rels_cross_company),
        ]
        if 'cctv.camera' in self.env:
            checks.insert(0, (self.env._("Cameras that would drop their events"),
                              self._cameras_without_reader_list))
        for title, fn in checks:
            start = time.time()
            try:
                offenders = fn()
            except Exception as e:  # noqa: BLE001 - one broken check must not
                # silence the others; a check that cannot run is itself a finding.
                _logger.warning("Consistency check %r failed to run: %s",
                                title, e, exc_info=True)
                self.results.append(self.b._make_result(
                    title, 0, 0, duration=time.time() - start,
                    status='error',
                    error=self.env._("the check itself could not run: %(error)s",
                                     error=e)))
                continue
            status, note = 'done', ''
            if offenders:
                note = self._name_them(offenders)
                inherited = self._same_shape_on_the_source(fn.__name__.lstrip('_'))
                if inherited is not None and inherited >= len(offenders):
                    # The other system has just as many. Worth saying - it is
                    # a real weakness of the installation - but it is not
                    # something this transfer did, and a red line here reads
                    # as "the transfer broke it".
                    status = 'partial'
                    note = self.env._(
                        "the other system has the same %(count)s - carried "
                        "over as it stands, not caused here: %(who)s",
                        count=inherited, who=note)
                else:
                    status = 'error'
            self.results.append(self.b._make_result(
                title, len(offenders), 0, skipped_count=len(offenders),
                duration=time.time() - start,
                status=status, error=note,
            ))
        return self.results

    def _name_them(self, offenders):
        shown = offenders[:NAMED_OFFENDERS]
        text = '; '.join(shown)
        if len(offenders) > len(shown):
            text += '; ' + self.env._("+%(count)s more",
                                      count=len(offenders) - len(shown))
        return text

    def _target_companies(self):
        return list((self.b.company_map or {}).values())

    # ── The invariants the running system relies on ───────────

    def _cameras_without_reader_list(self):
        """The event handler reads the camera's OWN reader list; readers
        merely pointing at the camera do not count. Empty list = every
        recognition dropped - the live defect this phase was born from."""
        Camera = self.env['cctv.camera'].sudo().with_context(active_test=False)
        offenders = []
        for camera in Camera.search(
                [('company_id', 'in', self._target_companies())]):
            if not camera.reader_ids:
                offenders.append(self.env._(
                    "camera %(name)s has an empty reader list - its "
                    "recognitions are being dropped", name=camera.display_name))
        return offenders

    def _controllers_behind_archived_module(self):
        """An archived module hides everything under it from every dotted
        company scope (an EXISTS never matches through it) - the equipment
        looks gone while it is merely veiled. Measured on a live source:
        one door, four readers and 143 events lived under two archived
        modules and every count missed them."""
        Ctrl = self.env['hr.rfid.ctrl'].sudo().with_context(active_test=False)
        offenders = []
        for ctrl in Ctrl.search(
                [('webstack_id.company_id', 'in', self._target_companies())]):
            if ctrl.webstack_id and not ctrl.webstack_id.active:
                offenders.append(self.env._(
                    "controller %(name)s hangs off archived module %(module)s",
                    name=ctrl.display_name,
                    module=ctrl.webstack_id.display_name))
        return offenders

    def _doors_off_the_chain(self):
        """A door reaches a company through its controller's module - or,
        with cameras installed, through a camera. One with neither is
        unattributable: invisible to scopes, unfixable from the UI."""
        Door = self.env['hr.rfid.door'].sudo().with_context(active_test=False)
        domain = [('controller_id', '=', False)]
        if 'camera_id' in Door._fields:
            domain += [('camera_id', '=', False)]
        return [self.env._("door %(name)s is attached to no equipment",
                           name=door.display_name)
                for door in Door.search(domain)]

    def _readers_without_door(self):
        """A reader records passages through its door; without one its
        events have nowhere to belong. ``door_id`` is computed, not stored -
        the walk is in Python, over the readers reachable through either
        chain."""
        Reader = self.env['hr.rfid.reader'].sudo().with_context(active_test=False)
        readers = Reader.search(
            [('controller_id.webstack_id.company_id', 'in',
              self._target_companies())])
        if 'camera_id' in Reader._fields:
            readers |= Reader.search(
                [('camera_id.company_id', 'in', self._target_companies())])
        return [self.env._("reader %(name)s has no door", name=reader.display_name)
                for reader in readers if not reader.door_id]

    def _chain_company_mismatch(self):
        """Every link of module -> controller -> door must stay inside ONE
        company; a mixed chain shows different equipment to different
        people and record rules quietly hide the mismatch itself."""
        Door = self.env['hr.rfid.door'].sudo().with_context(active_test=False)
        offenders = []
        for door in Door.search(
                [('controller_id.webstack_id.company_id', 'in',
                  self._target_companies())]):
            module_company = door.controller_id.webstack_id.company_id
            if (door.company_id and module_company
                    and door.company_id != module_company):
                offenders.append(self.env._(
                    "door %(door)s is of %(door_company)s while its module "
                    "belongs to %(module_company)s",
                    door=door.display_name,
                    door_company=door.company_id.display_name,
                    module_company=module_company.display_name))
        return offenders

    def _cards_with_foreign_owner(self):
        """A card of one company held by a person of another crosses the
        record rules: the card works, but the people managing that company
        cannot see why."""
        Card = self.env['hr.rfid.card'].sudo().with_context(active_test=False)
        offenders = []
        for card in Card.search(
                [('company_id', 'in', self._target_companies())]):
            owner = card.employee_id or card.contact_id
            owner_company = getattr(owner, 'company_id', False)
            if owner_company and card.company_id and owner_company != card.company_id:
                offenders.append(self.env._(
                    "card %(number)s of %(company)s is held by %(owner)s of "
                    "%(owner_company)s", number=card.number,
                    company=card.company_id.display_name,
                    owner=owner.display_name,
                    owner_company=owner_company.display_name))
        return offenders

    def _doors_without_readers(self):
        """A door nobody reads for cannot grant or refuse anyone."""
        Door = self.env['hr.rfid.door'].sudo().with_context(active_test=False)
        return [self.env._("door %(name)s has no readers", name=door.display_name)
                for door in Door.search(
                    [('company_id', 'in', self._target_companies()),
                     ('reader_ids', '=', False)])]

    def _readers_without_owner(self):
        """Every reader hangs off a controller or (with cameras installed)
        a camera; one with neither answers to nothing and its events can
        never be attributed."""
        Reader = self.env['hr.rfid.reader'].sudo().with_context(active_test=False)
        domain = [('controller_id', '=', False)]
        if 'camera_id' in Reader._fields:
            domain += [('camera_id', '=', False)]
        return [self.env._("reader %(name)s is attached to no equipment",
                           name=reader.display_name)
                for reader in Reader.search(domain)]

    def _cards_without_owner(self):
        """A card with no employee and no contact opens doors for nobody -
        and can never be blocked through a person either."""
        Card = self.env['hr.rfid.card'].sudo().with_context(active_test=False)
        return [self.env._("card %(number)s belongs to nobody", number=card.number)
                for card in Card.search(
                    [('company_id', 'in', self._target_companies()),
                     ('employee_id', '=', False), ('contact_id', '=', False)])]

    def _door_rels_cross_company(self):
        """An access group granting a door of ANOTHER company is a leak the
        record rules will later hide from the very people managing it."""
        Rel = self.env['hr.rfid.access.group.door.rel'].sudo()
        offenders = []
        for rel in Rel.search(
                [('access_group_id.company_id', 'in', self._target_companies())]):
            if (rel.door_id.company_id and rel.access_group_id.company_id
                    and rel.door_id.company_id != rel.access_group_id.company_id):
                offenders.append(self.env._(
                    "group %(group)s grants door %(door)s of another company",
                    group=rel.access_group_id.display_name,
                    door=rel.door_id.display_name))
        return offenders

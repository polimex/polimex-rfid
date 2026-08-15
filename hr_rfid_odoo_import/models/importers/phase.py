# -*- coding: utf-8 -*-
"""The phases of a transfer, and the rule for which of them can run.

Each phase declares what it needs. The registry is the single source of truth
for both the order and the list of features probed on the source: a hardcoded
list kept somewhere else falls behind silently, and that is exactly how the
cameras went missing - the wizard asked the source about six module names, none
of which was the camera one, so the operator got a clean-looking run with no
camera data and no warning either.
"""
import logging

_logger = logging.getLogger(__name__)


def _target_available(env, requirement):
    """Whether this system can receive that kind of data.

    ``requirement`` is a model name, or a (model, field) pair.

    Presence of the model is not enough, for two separate reasons. An abstract
    model resolves in the registry but owns no table, so a gate keyed on the
    name alone would report a capability that cannot store a single row. And a
    model whose schema differs between versions carries the name but not the
    column the bulk insert will name, which fails as UndefinedColumn halfway
    through the phase rather than before it starts.
    """
    name, field = requirement if isinstance(requirement, tuple) else (requirement, None)
    if name not in env:
        return False
    model = env[name]
    if getattr(model, '_abstract', False) or getattr(model, '_transient', False):
        return False
    if field and field not in model._fields:
        return False
    return True


class PhaseImporter:
    """What every phase of the transfer has in common.

    The metadata below used to live as literals in the wizard's import loop.
    Moving it onto the phase is what lets the wizard stop knowing the name of
    any particular feature.
    """

    #: Label used in the transfer log, e.g. 'Phase 4'.
    PHASE_ID = ''
    #: Name shown to the operator.
    NAME = ''
    #: Modules that must be installed on the SOURCE for this phase to mean anything.
    REQUIRES_SOURCE = ()
    #: Models (or (model, field) pairs) this system needs in order to receive the data.
    REQUIRES_TARGET = ()
    #: Key in the options dict; the phase runs only when it is set.
    OPTION = ''
    #: Several keys, any one of which is enough. For phases that cover more
    #: than one kind of data (events: user, system, temperature) and gate each
    #: kind internally. Without this the phase would start whenever the module
    #: is present, do nothing, and report success - which reads exactly like
    #: "there was no data".
    OPTION_ANY = ()
    #: Relative share of the progress bar.
    WEIGHT = 1

    def __init__(self, base):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        raise NotImplementedError

    def steps(self, *steps):
        """Run the steps of this phase, each one on its own.

        One step failing must not take the rest of the phase with it. The case
        that forced this is ordinary rather than exotic: the account used to
        read the other system is often not allowed to see every model - a real
        customer's Odoo 17 refused the emergency-signal groups outright - and
        the whole hardware phase died on it, so the controllers, doors, readers
        and everything after them never arrived either.

        A step that cannot run is recorded with what went wrong and the phase
        carries on. Nothing is hidden: the line says the step failed.
        """
        for step in steps:
            name = step.__name__.lstrip('_').replace('_', ' ')
            try:
                with self.env.cr.savepoint():
                    step()
            except Exception as exc:
                _logger.warning("Step %s could not be completed: %s",
                                name, exc, exc_info=True)
                self.results.append(self.b._make_result(
                    name, 0, 0, status='error',
                    error=self.env._(
                        "This part could not be read from the other system: "
                        "%(problem)s", problem=str(exc)[:200],
                    ),
                ))
        return self.results


def registry():
    """The phases, built on first use.

    Lazily, because the phase modules import ``PhaseImporter`` from here: doing
    the work at import time makes the two files import each other and the whole
    module fails to load.
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_registry()
    return _REGISTRY


def _skip_reason(env, cls, options, source_modules):
    """Why this phase will not run, in words the operator can act on."""
    if cls.OPTION and not options.get(cls.OPTION):
        return env._("Left out of this transfer.")
    if cls.OPTION_ANY and not any(options.get(o) for o in cls.OPTION_ANY):
        return env._("Left out of this transfer.")
    if any(m not in source_modules for m in cls.REQUIRES_SOURCE):
        return env._("The other system does not keep this kind of data.")
    if any(not _target_available(env, r) for r in cls.REQUIRES_TARGET):
        return env._(
            "This system cannot take over that data yet. Add the capability "
            "here first, then run the transfer again."
        )
    return None


def phase_plan(env, options, source_modules):
    """[(phase class, reason it is skipped or None)] in execution order.

    A pure function: no network, no writes. That is deliberate - the order, the
    gates and the reasons are the part most likely to drift, and they should be
    checkable in a fast test rather than only observable after a real run.
    """
    return [
        (cls, _skip_reason(env, cls, options, source_modules))
        for cls in registry()
    ]


def source_probe_modules():
    """Every module the source is asked about, derived from the phases."""
    return sorted({m for cls in registry() for m in cls.REQUIRES_SOURCE})


def total_weight():
    """Sum of the phase weights, for turning them into a progress range."""
    return sum(cls.WEIGHT for cls in registry()) or 1


def build_registry():
    """The phases, in the order they must run.

    The order carries meaning and is asserted by a test, not by a comment:
    - People before Zones, because zone membership and notification recipients
      are the people Phase 2 creates. Running zones with the hardware left
      every membership list empty, and those rows are written noupdate, so a
      later run could not repair them.
    - Sites after the hardware (they have equipment to hold) and before Access
      (the access groups point back at them), with their own access groups
      restored only AFTER Access, so a site does not build a group beside the
      one arriving from the source.
    - Cameras after Access, because the card-to-door rights regenerate during
      Access and that path mirrors into the camera plate lists. The order is
      the second line of defence; the first is the guard in polimex_ip_cam.
    """
    from .core_importer import CoreImporter, IoTableImporter, ZoneImporter
    from .people_importer import PeopleImporter
    from .leave_importer import LeaveImporter
    from .access_importer import AccessImporter
    from .camera_importer import CameraImporter
    from .site_importer import SiteGroupImporter, SiteImporter
    from .event_importer import EventImporter
    from .vending_importer import VendingImporter
    from .attendance_importer import AttendanceImporter
    from .service_importer import ServiceImporter
    return [
        CoreImporter,
        PeopleImporter,
        LeaveImporter,
        ZoneImporter,
        SiteImporter,
        AccessImporter,
        SiteGroupImporter,
        CameraImporter,
        EventImporter,
        VendingImporter,
        AttendanceImporter,
        ServiceImporter,
        IoTableImporter,
    ]


#: Filled by :func:`registry` on first use - never at import time.
_REGISTRY = None


def capabilities_the_target_lacks(env, options, source_modules):
    """[(phase class, wanted)] - data the source keeps but this system cannot
    take over yet.

    Derived from the phase registry, never from a hand-kept list: the wizard
    carried exactly such a list (vending, attendance, service) and the cameras
    were not on it - so a live migration learnt about the missing camera
    capability from the protocol AFTER the run, instead of from a warning
    before it. ``wanted`` says whether the operator has actually switched that
    data on, so the caller can block (wanted) or merely inform (not wanted).
    """
    out = []
    for cls in registry():
        if not cls.REQUIRES_SOURCE:
            continue
        if any(m not in source_modules for m in cls.REQUIRES_SOURCE):
            continue
        if all(_target_available(env, r) for r in cls.REQUIRES_TARGET):
            continue
        wanted = ((not cls.OPTION or bool(options.get(cls.OPTION)))
                  and (not cls.OPTION_ANY
                       or any(options.get(o) for o in cls.OPTION_ANY)))
        out.append((cls, wanted))
    return out

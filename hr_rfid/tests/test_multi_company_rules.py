# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression tests: multi-company record rules must tolerate company_id=False.

The company rules used the strict form [('company_id', 'in', company_ids)]
(or its dotted variants), which hides every global / shared record — and
every record whose company chain ends in NULL — from all non-superusers.

Fixed forms under test (security/hr_rfid_multi_company.xml):
- hr.rfid.workcode      [('company_id', 'in', company_ids + [False])]
- hr.rfid.door          [('company_id', 'in', company_ids + [False])]
                        (door.company_id is a stored compute that yields
                        False when the door has no webstack)
- hr.rfid.reader        ['|', ('webstack_id.company_id', '=', False),
                              ('webstack_id.company_id', 'in', company_ids)]
- hr.rfid.event.system  ['|', ('controller_id.webstack_id.company_id', '=', False),
                              ('controller_id.webstack_id.company_id', 'in', company_ids)]

The production-proven bug case is hr.rfid.event.system records created
WITHOUT controller_id — controllers/main.py creates controller-less system
events on every unhandled exception. Those records MUST stay visible to a
company-bound non-superuser RFID user.
"""
from odoo import fields
from odoo.tests.common import tagged, new_test_user
from odoo.tools import mute_logger

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


# Record rules are the whole subject here, and the rule the DATABASE holds is
# not always the one this module ships: polimex_ip_cam overrides several of
# them by xml id, to let a camera's own company answer for events its hardware
# chain cannot. At install time those rules are already in place while the
# camera module's FIELDS are not yet loaded, so reading anything through them
# raises KeyError: 'camera_id' - a red suite on every database that has the
# camera module, curable only by updating hr_rfid in the same command, which
# nobody should have to know. Post-install is also the honest moment to ask
# these questions: what a user may see is decided by the rules an installation
# ENDS UP with, not by ours in isolation.
@tagged('standard', 'post_install', '-at_install', 'rfid', 'rfid_security')
class TestMultiCompanySharedRecords(RFIDAppCase):
    """Global (no-company) records visible; other-company records hidden."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A genuinely different company is required for the inverse
        # (isolation) assertions. RFIDAppCase falls back to the same
        # company when the DB has only one — create a dedicated one then.
        other = cls.env['res.company'].sudo().search(
            [('id', '!=', cls.test_company_id)], limit=1)
        cls.company_b = other or cls.env['res.company'].create(
            {'name': 'RFID Comp Rule Co B'})
        # Officer: read access on workcode, door, reader and event.system
        # (officer implies viewer), bound to company A ONLY so the record
        # rule — not the ACL — is what is under test.
        cls.rule_user = new_test_user(
            cls.env,
            login='rfid_comp_rule_officer',
            groups='hr_rfid.hr_rfid_group_officer',
            name='RFID Comp Rule Officer',
            company_id=cls.test_company_id,
            company_ids=[(6, 0, [cls.test_company_id])],
        )
        # Company-B hardware chain for the inverse assertions.
        cls.webstack_b = cls.env['hr.rfid.webstack'].create({
            'name': 'Comp Rule Stack B',
            'serial': '887766',
            'company_id': cls.company_b.id,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        cls.ctrl_b = cls.env['hr.rfid.ctrl'].create({
            'name': 'Comp Rule Ctrl B',
            'webstack_id': cls.webstack_b.id,
            'ctrl_id': 1,
        })

    def _visible(self, model, record):
        """Search the record as the company-A-bound non-superuser."""
        return self.env[model].with_user(self.rule_user).search(
            [('id', '=', record.id)])

    @classmethod
    def _free_workcodes(cls, count):
        """Workcode has a global UNIQUE(workcode) constraint — pick codes
        not present in the target database."""
        existing = set(
            cls.env['hr.rfid.workcode'].sudo().search([]).mapped('workcode'))
        codes = []
        for i in range(9999, 8999, -1):
            code = '%04d' % i
            if code not in existing:
                codes.append(code)
                if len(codes) == count:
                    return codes
        raise AssertionError('Could not find %d free workcodes' % count)

    # ------------------------------------------------------------------
    # hr.rfid.workcode — direct company_id, [('company_id','in',cids+[False])]
    # ------------------------------------------------------------------
    def test_workcode_global_visible(self):
        """A workcode with company_id=False is shared — must be visible."""
        code = self._free_workcodes(1)[0]
        workcode = self.env['hr.rfid.workcode'].create({
            'name': 'Comp Rule Global WC',
            'workcode': code,
            'company_id': False,
        })
        self.assertEqual(
            self._visible('hr.rfid.workcode', workcode), workcode,
            'global (no-company) workcode must be visible to a company-A '
            'user — the company rule must tolerate company_id=False',
        )

    def test_workcode_other_company_hidden(self):
        """Tolerating False must NOT leak other companies' workcodes."""
        code = self._free_workcodes(2)[1]
        workcode = self.env['hr.rfid.workcode'].create({
            'name': 'Comp Rule Co-B WC',
            'workcode': code,
            'company_id': self.company_b.id,
        })
        self.assertFalse(
            self._visible('hr.rfid.workcode', workcode),
            'company-B workcode must stay hidden from a company-A user',
        )

    # ------------------------------------------------------------------
    # hr.rfid.door — stored computed company_id (False when no webstack)
    # ------------------------------------------------------------------
    def test_door_without_webstack_visible(self):
        """A door with no controller/webstack computes company_id=False —
        it must remain visible to a company-bound user."""
        door = self.env['hr.rfid.door'].create({
            'name': 'Comp Rule Orphan Door',
            'number': 1,
        })
        self.assertFalse(
            door.company_id,
            'precondition: a no-webstack door must compute company_id=False')
        self.assertEqual(
            self._visible('hr.rfid.door', door), door,
            'door with computed company_id=False must be visible to a '
            'company-A user — the company rule must tolerate False',
        )

    def test_door_other_company_hidden(self):
        """A door wired to a company-B controller must stay hidden."""
        door = self.env['hr.rfid.door'].create({
            'name': 'Comp Rule Co-B Door',
            'number': 1,
            'controller_id': self.ctrl_b.id,
        })
        self.assertEqual(
            door.company_id, self.company_b,
            'precondition: door behind company-B webstack computes company B')
        self.assertFalse(
            self._visible('hr.rfid.door', door),
            'company-B door must stay hidden from a company-A user',
        )

    # ------------------------------------------------------------------
    # hr.rfid.reader — dotted rule on webstack_id.company_id
    # ------------------------------------------------------------------
    def test_reader_without_controller_visible(self):
        """A reader with controller_id=False has webstack_id=False (related
        via controller) — the '|' False branch must match it."""
        reader = self.env['hr.rfid.reader'].create({
            'name': 'Comp Rule Orphan Reader',
            'number': 1,
            'reader_type': '0',
        })
        self.assertFalse(
            reader.webstack_id,
            'precondition: a controller-less reader has no webstack')
        self.assertEqual(
            self._visible('hr.rfid.reader', reader), reader,
            'controller-less reader (webstack chain ends in NULL) must be '
            'visible to a company-A user — '
            "the ('webstack_id.company_id', '=', False) branch must match "
            'a reader whose webstack_id itself is False (dotted falsy-leaf '
            'semantics)',
        )

    def test_reader_other_company_hidden(self):
        """A reader on a company-B controller must stay hidden."""
        reader = self.env['hr.rfid.reader'].create({
            'name': 'Comp Rule Co-B Reader',
            'number': 1,
            'reader_type': '0',
            'controller_id': self.ctrl_b.id,
        })
        self.assertEqual(reader.webstack_id, self.webstack_b)
        self.assertFalse(
            self._visible('hr.rfid.reader', reader),
            'company-B reader must stay hidden from a company-A user',
        )

    # ------------------------------------------------------------------
    # hr.rfid.event.system — TASK ZERO: controller-less system events
    # (production case: controllers/main.py creates them on exceptions)
    # ------------------------------------------------------------------
    def test_event_system_controller_less_visible(self):
        """PRODUCTION BUG CASE: a system event created without controller_id
        (exactly what controllers/main.py does on every unhandled exception)
        must be visible to a company-bound non-superuser.

        If this FAILS, Odoo 19's dotted domain
        ('controller_id.webstack_id.company_id', '=', False) does NOT match
        records with controller_id=False — the rule then needs an extra
        ('controller_id', '=', False) branch.
        """
        # Production-mirror shape: webstack set (company A), no controller.
        event_ws = self.env['hr.rfid.event.system'].create({
            'webstack_id': self.test_webstack_10_3_id.id,
            'controller_id': False,
            'timestamp': fields.Datetime.now(),
            'error_description': 'Comp rule regression: ws-only event',
        })
        # Bare shape: the generic exception handler writes webstack_id=False
        # too when the webstack could not be resolved.
        event_bare = self.env['hr.rfid.event.system'].create({
            'webstack_id': False,
            'controller_id': False,
            'timestamp': fields.Datetime.now(),
            'error_description': 'Comp rule regression: bare event',
        })
        self.assertTrue(event_ws and not event_ws.controller_id)
        self.assertTrue(event_bare and not event_bare.controller_id)

        self.assertEqual(
            self._visible('hr.rfid.event.system', event_ws), event_ws,
            'DOTTED-FALSY SEMANTICS NOT MATCHED: controller-less system '
            'event (webstack set, controller_id=False) is INVISIBLE to a '
            'company-bound user — '
            "('controller_id.webstack_id.company_id', '=', False) does not "
            'match controller_id=False in Odoo 19; the rule needs an extra '
            "('controller_id', '=', False) branch",
        )
        self.assertEqual(
            self._visible('hr.rfid.event.system', event_bare), event_bare,
            'DOTTED-FALSY SEMANTICS NOT MATCHED: bare system event '
            '(no webstack, no controller) is INVISIBLE to a company-bound '
            'user — the rule needs an extra '
            "('controller_id', '=', False) branch",
        )

    def test_event_system_other_company_hidden(self):
        """A system event of a company-B controller must stay hidden."""
        event_b = self.env['hr.rfid.event.system'].create({
            'webstack_id': self.webstack_b.id,
            'controller_id': self.ctrl_b.id,
            'timestamp': fields.Datetime.now(),
            'error_description': 'Comp rule regression: company-B event',
        })
        self.assertTrue(event_b)
        self.assertFalse(
            self._visible('hr.rfid.event.system', event_b),
            'company-B system event must stay hidden from a company-A user',
        )


@tagged('standard', 'post_install', '-at_install', 'rfid', 'rfid_security')
class TestOrphanUserEventVisibility(RFIDAppCase):
    """Owner decision 5: an event that names NOBODY (unknown card) belongs
    to the door where it happened - the company operating that door, and
    the companies the module is shared with, see it; everyone else does
    not. Only when the hardware chain is broken (no reader, or a chain
    ending in a company-less module) does the event stay visible to all,
    because hiding it would bring back the visible-to-no-one defect.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].browse(cls.test_company_id)
        cls.company_b = cls.env['res.company'].create(
            {'name': 'Orphan Rule Co B'})

        # One restricted (non-superuser) events reader per company: the
        # record rule, not the ACL, is what decides who sees what.
        cls.user_a = new_test_user(
            cls.env,
            login='rfid_orphan_officer_a',
            groups='hr_rfid.hr_rfid_group_officer',
            name='Orphan Rule Officer A',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )
        cls.user_b = new_test_user(
            cls.env,
            login='rfid_orphan_officer_b',
            groups='hr_rfid.hr_rfid_group_officer',
            name='Orphan Rule Officer B',
            company_id=cls.company_b.id,
            company_ids=[(6, 0, [cls.company_b.id])],
        )

        def _chain(webstack, ctrl_id, tag):
            ctrl = cls.env['hr.rfid.ctrl'].create({
                'name': 'Orphan Rule Ctrl %s' % tag,
                'webstack_id': webstack.id,
                'ctrl_id': ctrl_id,
            })
            return cls.env['hr.rfid.reader'].create({
                'name': 'Orphan Rule Reader %s' % tag,
                'number': 1,
                'reader_type': '0',
                'controller_id': ctrl.id,
            })

        # Company-A hardware: reuse the base fixture module (company A).
        cls.reader_a = _chain(cls.test_webstack_10_3_id, 81, 'A')
        # Company-B hardware.
        cls.webstack_b = cls.env['hr.rfid.webstack'].create({
            'name': 'Orphan Rule Stack B',
            'serial': '664401',
            'company_id': cls.company_b.id,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        cls.reader_b = _chain(cls.webstack_b, 82, 'B')
        # Module owned by B and SHARED with A (Laravel customer_web_stack
        # parity - one physical entrance serving two companies).
        cls.webstack_shared = cls.env['hr.rfid.webstack'].create({
            'name': 'Orphan Rule Shared Stack',
            'serial': '664402',
            'company_id': cls.company_b.id,
            'shared_company_ids': [(6, 0, [cls.company_a.id])],
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        cls.reader_shared = _chain(cls.webstack_shared, 83, 'S')
        # Module with NO owner company - the chain resolves to nobody.
        cls.webstack_nocomp = cls.env['hr.rfid.webstack'].create({
            'name': 'Orphan Rule No-Company Stack',
            'serial': '664403',
            'company_id': False,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        cls.reader_nocomp = _chain(cls.webstack_nocomp, 84, 'N')
        # Reader wired to no controller at all - chain broken one link in.
        cls.reader_broken = cls.env['hr.rfid.reader'].create({
            'name': 'Orphan Rule Broken Reader',
            'number': 1,
            'reader_type': '0',
        })

        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Orphan Rule Emp B',
            'company_id': cls.company_b.id,
        })

        def _orphan(reader):
            # An unknown card names nobody: no employee, no contact, no
            # card. The model logs an ERROR line for that shape by design;
            # mute it so the log-error watchdog does not fail the fixture.
            with mute_logger(
                    'odoo.addons.hr_rfid.models.hr_rfid_event_user'):
                return cls.env['hr.rfid.event.user'].create({
                    'reader_id': reader.id,
                    'event_action': '2',
                    'event_time': fields.Datetime.now(),
                })

        cls.ev_orphan_a = _orphan(cls.reader_a)
        cls.ev_orphan_b = _orphan(cls.reader_b)
        cls.ev_orphan_shared = _orphan(cls.reader_shared)
        cls.ev_orphan_nocomp = _orphan(cls.reader_nocomp)
        cls.ev_orphan_broken = _orphan(cls.reader_broken)

        # Reader-LESS orphan: reader_id is required today, but migrated
        # databases predate that requirement and hold such rows (Odoo
        # cannot apply NOT NULL over existing NULLs on upgrade - it keeps
        # them and logs a warning). Reproduce that legacy shape: relax the
        # constraint inside the test transaction (rolled back afterwards)
        # and insert the row the way old data actually sits in the table.
        cls.env.cr.execute(
            "ALTER TABLE hr_rfid_event_user"
            " ALTER COLUMN reader_id DROP NOT NULL")
        cls.env.cr.execute(
            """INSERT INTO hr_rfid_event_user
                   (event_time, event_action,
                    create_date, write_date, create_uid, write_uid)
               VALUES (now() at time zone 'UTC', '2',
                       now() at time zone 'UTC', now() at time zone 'UTC',
                       %s, %s)
               RETURNING id""",
            [cls.env.uid, cls.env.uid])
        cls.ev_orphan_readerless = cls.env['hr.rfid.event.user'].browse(
            cls.env.cr.fetchone()[0])

        # Identified events for the negative assertions.
        cls.ev_emp_a_on_reader_b = cls.env['hr.rfid.event.user'].create({
            'reader_id': cls.reader_b.id,
            'employee_id': cls.test_employee_id.id,
            'event_action': '2',
            'event_time': fields.Datetime.now(),
        })
        cls.ev_emp_b_on_reader_a = cls.env['hr.rfid.event.user'].create({
            'reader_id': cls.reader_a.id,
            'employee_id': cls.employee_b.id,
            'event_action': '2',
            'event_time': fields.Datetime.now(),
        })
        cls.ev_emp_b_on_reader_b = cls.env['hr.rfid.event.user'].create({
            'reader_id': cls.reader_b.id,
            'employee_id': cls.employee_b.id,
            'event_action': '2',
            'event_time': fields.Datetime.now(),
        })

    def _sees(self, user, event):
        return bool(self.env['hr.rfid.event.user'].with_user(user).search(
            [('id', '=', event.id)]))

    # ------------------------------------------------------------------
    # (a) an orphan belongs to the company operating the door
    # ------------------------------------------------------------------
    def test_orphan_visible_to_door_owner(self):
        """The security officer of the company operating a door must see
        an unknown card presented at that door - it is THEIR incident."""
        self.assertTrue(
            self._sees(self.user_a, self.ev_orphan_a),
            'orphan event on a company-A reader must be visible to the '
            'company-A officer',
        )
        self.assertTrue(
            self._sees(self.user_b, self.ev_orphan_b),
            'orphan event on a company-B reader must be visible to the '
            'company-B officer',
        )

    def test_orphan_hidden_from_other_company(self):
        """NEGATIVE: another company's officer must NOT see an unknown
        card presented at a door that is not theirs - the old rule showed
        every orphan to every company."""
        self.assertFalse(
            self._sees(self.user_b, self.ev_orphan_a),
            'orphan event on a company-A reader must stay hidden from the '
            'company-B officer - the orphan branch is no longer global',
        )
        self.assertFalse(
            self._sees(self.user_a, self.ev_orphan_b),
            'orphan event on a company-B reader must stay hidden from the '
            'company-A officer - the orphan branch is no longer global',
        )

    # ------------------------------------------------------------------
    # (b) shared module: the sharing company sees the door's orphans too
    # ------------------------------------------------------------------
    def test_orphan_on_shared_module_visible_to_sharing_company(self):
        """Two companies sharing one entrance both guard it: the sharing
        company's officer must see an unknown card at the shared door,
        exactly as they see its system events (rule parity)."""
        self.assertTrue(
            self._sees(self.user_b, self.ev_orphan_shared),
            'orphan event on the shared module must be visible to its '
            'OWNER company officer',
        )
        self.assertTrue(
            self._sees(self.user_a, self.ev_orphan_shared),
            'orphan event on a module shared with company A must be '
            'visible to the company-A officer (shared_company_ids branch)',
        )

    # ------------------------------------------------------------------
    # (c) broken chain: the orphan must not become invisible to everyone
    # ------------------------------------------------------------------
    def test_orphan_without_reader_stays_visible(self):
        """A legacy imported event with NO reader resolves to no company;
        narrowing must not hide it from everyone - that would recreate
        the visible-to-no-one defect the orphan branch was born to fix."""
        self.assertTrue(
            self._sees(self.user_a, self.ev_orphan_readerless),
            'reader-less orphan event must remain visible to company A - '
            "the ('reader_id', '=', False) fallback branch must match",
        )
        self.assertTrue(
            self._sees(self.user_b, self.ev_orphan_readerless),
            'reader-less orphan event must remain visible to company B - '
            "the ('reader_id', '=', False) fallback branch must match",
        )

    def test_orphan_broken_chain_stays_visible(self):
        """A chain that stops before naming a company (reader with no
        controller; module with no owner company) also resolves to
        nobody - such orphans stay visible instead of vanishing. Each
        optional link needs its own branch: a dotted '= False' never
        matches a NULL intermediate link in Odoo 19."""
        for event, label in [
            (self.ev_orphan_broken, 'controller-less reader'),
            (self.ev_orphan_nocomp, 'company-less module'),
        ]:
            self.assertTrue(
                self._sees(self.user_a, event),
                'orphan event on a %s must remain visible to company A' %
                label,
            )
            self.assertTrue(
                self._sees(self.user_b, event),
                'orphan event on a %s must remain visible to company B' %
                label,
            )

    # ------------------------------------------------------------------
    # (d) NEGATIVE: an identified event never rides the orphan branch
    # ------------------------------------------------------------------
    def test_identified_event_ignores_hardware_chain(self):
        """An event that DOES name a person is governed by that person's
        company, not by the door: company A still sees its employee badge
        at a foreign door, and a foreign employee at company A's own door
        stays the foreign company's business."""
        self.assertTrue(
            self._sees(self.user_a, self.ev_emp_a_on_reader_b),
            'event of a company-A employee on a company-B reader must stay '
            'visible to company A - the employee branch, not the hardware '
            'chain, decides for identified events',
        )
        self.assertFalse(
            self._sees(self.user_a, self.ev_emp_b_on_reader_a),
            'event of a company-B employee on a company-A reader must stay '
            'hidden from company A - the new hardware-chain branch must '
            'not leak identified events',
        )

    # ------------------------------------------------------------------
    # (e) NEGATIVE: a foreign identified event stays hidden
    # ------------------------------------------------------------------
    def test_foreign_identified_event_stays_hidden(self):
        """Company A must not see another company's employee events at
        that company's own doors - the pre-existing isolation survives
        the orphan-branch change untouched."""
        self.assertFalse(
            self._sees(self.user_a, self.ev_emp_b_on_reader_b),
            'company-B employee event on company-B hardware must stay '
            'hidden from the company-A officer',
        )
        self.assertTrue(
            self._sees(self.user_b, self.ev_emp_b_on_reader_b),
            'company-B employee event must remain visible to the '
            'company-B officer',
        )

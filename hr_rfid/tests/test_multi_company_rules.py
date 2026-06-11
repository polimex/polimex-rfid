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

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_security')
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

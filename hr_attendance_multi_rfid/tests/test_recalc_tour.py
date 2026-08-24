# -*- coding: utf-8 -*-
"""Looking at a running rebuild must never break the screen.

The rebuild works in the background and the form does not move on its own, so
the operator presses Refresh to look again. On a live site that press put a
server error on the screen: the button wrote the state of the very record the
worker was updating, the two transactions met on the same row, and the web
request lost with "could not serialize access due to concurrent update".

Nothing in the model tests could see it - they call methods, they do not press
buttons. This one presses the button.
"""
from datetime import date, timedelta

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'rfid_attendance_recalc',
        'rfid_recalc_tour')
class TestTheOperatorCanWatchARebuild(HttpCase):

    # A tour drives the real web client, which needs to write to the database
    # the way a user does.
    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Rebuild Watcher',
            'company_id': cls.env.company.id,
        })
        # A rebuild that is waiting to start - the state the operator sits and
        # watches, and the state the broken button was pressed in.
        cls.rebuild = cls.env['hr.attendance.recalc.run'].create({
            'employee_ids': [Command.set(cls.employee.ids)],
            'date_from': date.today() - timedelta(days=7),
            'date_to': date.today(),
        })

    def test_pressing_refresh_does_not_break_the_screen(self):
        """The operator opens the rebuild, presses Refresh, and is still
        looking at the rebuild afterwards."""
        self.assertEqual(self.rebuild.state, 'queued')
        written_at = self.rebuild.write_date

        self.start_tour(
            "/odoo/action-hr_attendance_multi_rfid.hr_attendance_recalc_run_action",
            "hr_attendance_recalc_refresh_tour",
            login="admin",
        )

        self.rebuild.invalidate_recordset()
        self.assertEqual(
            self.rebuild.write_date, written_at,
            "looking at a rebuild must not write to it - that is what "
            "collided with the worker and put a server error on screen")
        self.assertEqual(self.rebuild.state, 'queued')

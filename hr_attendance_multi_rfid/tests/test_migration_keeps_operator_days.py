# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""The 19.0.1.5.3 upgrade gives the machine its days and leaves people theirs.

The upgrade marks as door-made ('rfid') the attendance an older version left
as 'manual', so that a rebuild of the period can replace it from the doors.
A day a person has corrected must never be among them: an operator who types
the check-out somebody forgot is stating a fact the doors do not hold, and a
rebuild deletes every door-made record of the period. Case of 12.10.2026,
reproduced on a customer clone: the check-in still matched a passage, the
upgrade handed the corrected day back to the machine, and the next rebuild
took the typed check-out away.

These tests run the upgrade step itself, from its file.
"""
import importlib.util
from datetime import timedelta

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import file_path

from .common import one_door, passage


def _upgrade_step():
    spec = importlib.util.spec_from_file_location(
        "hr_attendance_multi_rfid_mig_19_0_1_5_3",
        file_path("hr_attendance_multi_rfid/migrations/19.0.1.5.3/post-migration.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.stamp_rfid_born_attendance


@tagged('post_install', '-at_install', 'rfid_attendance_migration')
class TestUpgradeKeepsOperatorDays(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A door with an entry and an exit reader and NO attendance zone: the
        # passages are recorded, the attendance is written by the test.
        cls.door, cls.reader_in, cls.reader_out = one_door(cls.env, 'Upgrade', 8846, 12)
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Upgrade Employee (test)', 'company_id': cls.env.company.id})
        yesterday = fields.Datetime.now() - timedelta(days=1)
        cls.came = yesterday.replace(hour=6, minute=0, second=17, microsecond=0)
        cls.left = cls.came + timedelta(hours=8, minutes=3, seconds=11)
        cls.stamp = staticmethod(_upgrade_step())

    def _passage(self, reader, moment):
        passage(self.employee, self.door, reader, moment)

    def _left_as_manual(self, check_in, check_out=None):
        """A record the way an older version left it: 'manual', whoever made it."""
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id, 'check_in': check_in,
            'check_out': check_out, 'in_mode': 'manual'})
        self.env.flush_all()
        return attendance

    def _upgrade(self):
        self.stamp(self.env.cr)
        self.env.invalidate_all()

    def test_a_day_the_doors_recorded_at_both_ends_goes_to_the_machine(self):
        """In and out both at a passage: the machine made it, and may rebuild it."""
        self._passage(self.reader_in, self.came)
        self._passage(self.reader_out, self.left)
        day = self._left_as_manual(self.came, self.left)

        self._upgrade()

        self.assertEqual(day.in_mode, 'rfid')

    def test_a_person_still_inside_goes_to_the_machine(self):
        """Only the entry exists yet, and it is a passage: the machine's record."""
        self._passage(self.reader_in, self.came)
        day = self._left_as_manual(self.came)

        self._upgrade()

        self.assertEqual(day.in_mode, 'rfid')

    def test_a_check_out_the_operator_typed_stays_the_operators(self):
        """The forgotten exit typed in by hand keeps the record with the person."""
        self._passage(self.reader_in, self.came)
        typed = self.left.replace(second=0)
        day = self._left_as_manual(self.came, typed)

        self._upgrade()

        self.assertEqual(
            day.in_mode, 'manual',
            "The upgrade handed a day an operator corrected back to the machine")

    def test_the_operators_day_survives_the_next_rebuild(self):
        """What the customer would see: the typed check-out is still there afterwards.

        The door counts attendance here, so the rebuild really replays it. The
        person came in at the door; the exit was missed, and an operator typed
        it in by hand - on the older version the record then simply read
        'manual'.
        """
        self.env['hr.rfid.zone'].create({
            'name': 'Upgrade Zone', 'company_id': self.env.company.id,
            'attendance': True, 'door_ids': [Command.link(self.door.id)]})
        self._passage(self.reader_in, self.came)
        day = self.env['hr.attendance'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(day), 1, "the entry must open the day")
        typed = self.left.replace(second=0)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_attendance SET in_mode = 'manual', check_out = %s WHERE id = %s",
            (typed, day.id))
        self.env.invalidate_all()

        self._upgrade()
        self.employee.recalc_attendance(
            fields.Date.to_date(self.came) - timedelta(days=1), fields.Date.today())

        self.assertTrue(day.exists(), "the rebuild deleted the operator's day")
        self.assertEqual(day.check_out, typed,
                         "the check-out the operator typed is gone after the rebuild")

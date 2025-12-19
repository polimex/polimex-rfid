from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools.float_utils import float_round, float_is_zero
import base64


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'

    department_id = fields.Many2one(
        store=True,
        help="Employee's department at the time of this attendance record. This field is stored "
             "to maintain historical accuracy even if the employee later changes departments."
    )

    check_in = fields.Datetime(
        index=True,
        help="Date and time when the employee checked in to work. This is automatically recorded "
             "when entering an RFID attendance zone or can be manually set by HR managers."
    )

    check_out = fields.Datetime(
        index=True,
        help="Date and time when the employee checked out from work. This is automatically recorded "
             "when leaving an RFID attendance zone or can be manually set by HR managers."
    )
    in_zone_id = fields.Many2one(
        'hr.rfid.zone',
        help="The RFID zone where this attendance session is taking place. Set when checking in "
             "and cleared when checking out. Used to track which area the employee is working in.",
        # compute='_compute_checkin_zone',
        # store=True
    )

    def _update_check_in(self, new):
        self.ensure_one()
        vals = {
            'employee_id': self.employee_id.id,
            'check_in': new,
            'in_zone_id': self.in_zone_id.id
        }
        self.unlink()
        self.flush()
        return self.create(vals)

    @api.depends('check_in', 'check_out')
    def _compute_checkin_zone(self):
        for att in self:
            if att.check_out:
                att.in_zone_id = False
            else:
                att_zones_ids = [self.employee_id.in_zone_ids.filtered(lambda z: z.attendance)]
                att.in_zone_id = att_zones_ids[0] or False

    def write(self, vals):
        for att in self:
            # in_zone_ids = att.employee_id.in_zone_ids.filtered(lambda z: z.attendance)
            if vals.get('check_out', False) and not att.check_out and att.in_zone_id:
                if self.env.context.get('from_event', None) is None:
                    att.in_zone_id.person_left(att.employee_id)
                vals['in_zone_id'] = False
        return super(HrAttendance, self).write(vals)

    def _get_zone_settings(self):
        self.ensure_one()
        att_zones_ids = self.employee_id.in_zone_ids.filtered(lambda z: z.attendance and z.max_time_in_zone)
        if att_zones_ids:
            # TODO multiple zone not proccessed!!!
            max_hours = att_zones_ids[0].max_time_in_zone
            return att_zones_ids[0].max_time_in_zone, att_zones_ids[0].auto_close_time_for_zone
        else:
            return False, False

    # inherited from hr_attendance_autoclose
    def needs_autoclose(self):
        self.ensure_one()
        max_time, autoclose = self._get_zone_settings()
        # TODO multiple zone not proccessed!!!
        if hasattr(super(), 'needs_autoclose'):
            max_hours = max_time or self.employee_id.company_id.attendance_maximum_hours_per_day
            close = not self.employee_id.no_autoclose
            return close and max_hours and self.open_worked_hours > max_hours
        else:
            max_hours = max_time
            close = not float_is_zero(max_time or 0.0, precision_digits=2)
            open_worked_hours = (fields.Datetime.now() - self.check_in).total_seconds() / 3600
            return close and max_hours and open_worked_hours > max_hours


    # inherited from hr_attendance_autoclose
    def autoclose_attendance(self, reason):
        self.ensure_one()
        max_time, autoclose = self._get_zone_settings()
        if hasattr(super(), 'autoclose_attendance'):
            max_hours = autoclose or self.employee_id.company_id.attendance_maximum_hours_per_day
            leave_time = self.check_in + timedelta(hours=max_hours)
            vals = {"check_out": leave_time}
            if reason:
                vals["attendance_reason_ids"] = [(4, reason.id)]
        else:
            max_hours = max_time
            leave_time = self.check_in + timedelta(hours=max_hours)
            vals = {"check_out": leave_time}
        self.write(vals)

    # inherited from hr_attendance_autoclose
    @api.model
    def check_for_incomplete_attendances(self):
        # Проверка дали функцията съществува в суперкласа
        if not hasattr(super(), 'check_for_incomplete_attendances'):
            # super().check_for_incomplete_attendances()
        # else:
            stale_attendances = self.search([("check_out", "=", False)])
            # reason = self.env.company.hr_attendance_autoclose_reason
            for att in stale_attendances.filtered(lambda a: a.needs_autoclose()):
                att.autoclose_attendance('')

    # bypass validity if old events processed
    def _check_validity(self):
        if self.env.context.get('no_validity_check', None) is None:
            super(HrAttendance, self)._check_validity()
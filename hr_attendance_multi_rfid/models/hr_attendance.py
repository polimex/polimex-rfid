from odoo import api, fields, models
from datetime import datetime, timedelta


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    department_id = fields.Many2one(store=True)

    check_in = fields.Datetime(
        index=True,
    )

    check_out = fields.Datetime(
        index=True,
    )
    in_zone_id = fields.Many2one(
        'hr.rfid.zone',
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


    @api.depends('check_in','check_out')
    def _compute_checkin_zone(self):
        for att in self:
            if att.check_out:
                att.in_zone_id = False
            else:
                att_zones_ids = [self.employee_id.in_zone_ids.filtered(lambda z: z.attendance)]
                att.in_zone_id = att_zones_ids[0] or False

    def write(self, vals):
        for att in self:
            in_zone_ids = att.employee_id.in_zone_ids.filtered(lambda z: z.attendance)
            if vals.get('check_out', False) and not att.check_out and in_zone_ids:
               in_zone_ids.person_left(att.employee_id)
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
        max_hours = max_time or self.employee_id.company_id.attendance_maximum_hours_per_day
        close = not self.employee_id.no_autoclose
        return close and max_hours and self.open_worked_hours > max_hours

    # inherited from hr_attendance_autoclose
    def autoclose_attendance(self, reason):
        self.ensure_one()
        max_time, autoclose = self._get_zone_settings()
        max_hours = autoclose or self.employee_id.company_id.attendance_maximum_hours_per_day
        leave_time = self.check_in + timedelta(hours=max_hours)
        vals = {"check_out": leave_time}
        if reason:
            vals["attendance_reason_ids"] = [(4, reason.id)]
        self.write(vals)

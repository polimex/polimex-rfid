from odoo import models, exceptions, _, api, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _last_open_checkin(self, zone_id):
        self.ensure_one()
        if zone_id:
            _last = self.env['hr.attendance'].search([
                ('employee_id', '=', self.id),
                ('check_out', '=', False),
                ('in_zone_id', '=', zone_id),
            ], limit=1)
            if _last:
                return _last
        return self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
        ], limit=1)



    def attendance_action_change_with_date(self, action_date, zone_id=None):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        self.ensure_one()

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
                'in_zone_id': zone_id
            }
            return self.env['hr.attendance'].create(vals)

        attendance = self.env['hr.attendance'].search([ ('employee_id', '=', self.id),
                                                        ('check_out', '=', False) ], limit=1)
        if attendance:
            attendance.check_out = action_date
        else:
            raise exceptions.UserError(_('Cannot perform check out on %(empl_name)s, '
                                         'could not find corresponding check in. Your '
                                         'attendances have probably been modified manually'
                                         ' by human resources.') % {'empl_name': self.name, })
        return attendance

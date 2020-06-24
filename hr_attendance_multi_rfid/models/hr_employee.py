from odoo import models, exceptions, _, api, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def attendance_action_change_with_date(self, action_date):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        self.ensure_one()

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
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

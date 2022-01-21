from odoo import models, exceptions, _, api, fields

#Traceback (most recent call last):
# File "/opt/odoo12/ext/hr_rfid/controllers/main.py", line 809, in post_event result = self._parse_event()
# File "/opt/odoo12/ext/hr_rfid/controllers/main.py", line 244, in _parse_event event = ev_env.create(event_dict)
# File "<decorator-gen-153>", line 2, in create
# File "/opt/odoo12/odoo/odoo/api.py", line 461, in _model_create_multi return create(self, [arg])
# File "/opt/odoo12/ext/hr_rfid/models/hr_rfid_webstack.py", line 1596, in create zones.person_went_through(rec)
# File "/opt/odoo12/ext/hr_rfid/models/hr_rfid_zone.py", line 63, in person_went_through zone.person_entered(person, event)
# File "/opt/odoo12/ext/hr_attendance_multi_rfid/models/hr_rfid_zone.py", line 43, in person_entered person.attendance_action_change_with_date(event.event_time)
# File "/opt/odoo12/ext/hr_attendance_multi_rfid/models/hr_employee.py", line 27, in attendance_action_change_with_date return self.env['hr.attendance'].create(vals)
# File "<decorator-gen-3>", line 2, in create
# File "/opt/odoo12/odoo/odoo/api.py", line 461, in _model_create_multi return create(self, [arg])
# File "/opt/odoo12/odoo/odoo/models.py", line 3583, in create records = self._create(data_list)
# File "/opt/odoo12/odoo/odoo/models.py", line 3715, in _create records._validate_fields(name for data in data_list for name in data['stored']) File "/opt/odoo12/odoo/odoo/models.py", line 1126, in _validate_fields check(self)
# File "/opt/odoo12/odoo/addons/hr_attendance/models/hr_attendance.py", line 84, in _check_validity 'datetime': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(no_check_out_attendances.check_in))), odoo.exceptions.ValidationError: ("Cannot create new attendance record for Яна Миланова, the employee hasn't checked out since 2021-12-26 07:15:04", None)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    theoretical_hours_start_date = fields.Date(
        help="Fill this field for setting a manual start date for computing "
             "the theoretical hours independently from the attendances. If "
             "not filled, employee creation date or the calendar start date "
             "will be used (the greatest of both).",
    )

    @api.multi
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

from odoo import models, exceptions, _, api, fields

import logging
_logger = logging.getLogger(__name__)



class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _last_open_checkin(self, zone_id=None):
        self.ensure_one()
        if zone_id is not None:
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

        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id),
                                                       ('check_out', '=', False)], limit=1)
        if attendance:
            attendance.check_out = action_date
        else:
            raise exceptions.UserError(_('Cannot perform check out on %(empl_name)s, '
                                         'could not find corresponding check in. Your '
                                         'attendances have probably been modified manually'
                                         ' by human resources.') % {'empl_name': self.name, })
        return attendance

    # TODO Recalculate attendance records (needed in some cases)
    def recalc_attendance(self, from_date, to_date: None, zone_id = None):
        if to_date is None:
            to_date = fields.Date.today()
        if zone_id is None:
            _logger.info('Search for first attendance zone...')
            zone_ids = self.env['hr.rfid.zone'].search([('attendance', '=', True)])
            zone_id =  zone_ids and zone_ids[0] or None
            if zone_id is None:
                _logger.error('No defined attendance zone for calculation')
        for e in self:
            pass
            # Clear old attendance records for the period
            # Search all events based on zone
            # Create all attendance records

from datetime import timedelta

from odoo import models, exceptions, _, api, fields
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _last_open_checkin(self, zone_id=None, before_dt=None):
        self.ensure_one()
        if zone_id is not None:
            domain = [
                ('employee_id', '=', self.id),
                ('check_out', '=', False),
                ('in_zone_id', '=', zone_id),
            ]
            if before_dt is not None:
                domain.append(('check_in', '<', before_dt))
            _last = self.env['hr.attendance'].search(domain, limit=1)
            if _last:
                return _last
        domain = [
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
        ]
        if before_dt is not None:
            domain.append(('check_in', '<', before_dt))
        return self.env['hr.attendance'].search(domain, limit=1)

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

    def recalc_attendance(self, from_date=None, to_date=None):
        if from_date is None:
            from_date = fields.Date.today() - timedelta(days=30)
        # if to_date is None:
        to_date = to_date or fields.Date.today()
        # if zone_id is None:
        #     _logger.info('Search for first attendance zone...')
        #     zone_ids = self.env['hr.rfid.zone'].search([('attendance', '=', True)])
        #     zone_id =  zone_ids and zone_ids[0] or None
        #     if zone_id is None:
        #         _logger.error('No defined attendance zone for calculation')
        att_zone_ids = self.env['hr.rfid.zone'].search([('attendance', "=", True)])
        doors_with_attendance = att_zone_ids.mapped('door_ids')
        readers_ids = doors_with_attendance.mapped('reader_ids')
        in_readers_ids = readers_ids.filtered(lambda r: r.reader_type == '0')
        out_readers_ids = readers_ids.filtered(lambda r: r.reader_type == '1')

        for employee_id in self:
            event_ids = self.env['hr.rfid.event.user'].search([
                ('employee_id', '=', employee_id.id),
                ('door_id', 'in', doors_with_attendance.mapped('id')),
                ('event_time', '>=', from_date),
                ('event_action', '=', '1')
            ], order='event_time')

            if not event_ids:  # no events for processing
                continue

            # Remove all attendance till now without manual
            auto_close_reason = False
            if self.env.company._fields.get('hr_attendance_autoclose_reason', False):
                auto_close_reason = self.env.company.hr_attendance_autoclose_reason and self.env.company.hr_attendance_autoclose_reason.id or False
            self.env['hr.attendance'].search([
                ('check_in', '>=', from_date),
                ('employee_id', '=', employee_id.id),
                ('|'),
                ('attendance_reason_ids', '=', False),
                ('attendance_reason_ids', '=', auto_close_reason),
            ]).unlink()
            manual_att_ids = self.env['hr.attendance'].search([
                ('check_in', '>=', from_date),
                ('employee_id', '=', employee_id.id),
            ])
            presence = [None, None]
            in_zone = None
            previous_attendance_id = None
            previous_event_id = None
            for e in event_ids:
                # Ignore events already recorded in attendance
                if manual_att_ids.filtered(lambda a: a.check_in == e.event_time or a.check_out == e.event_time):
                    continue
                e.in_or_out = 'no_info'
                # Make New presence Checkin or override last one if needed
                if ((presence[0] and in_zone.overwrite_check_in) or (
                not presence[0])) and e.reader_id in in_readers_ids:
                    if presence[0] and in_zone.overwrite_check_in and previous_event_id:
                        previous_event_id.in_or_out = 'no_info'
                    presence[0] = e.event_time
                    e.in_or_out = 'in'
                    in_zone = att_zone_ids.filtered(lambda z: e.door_id in z.door_ids)
                # Make Checkout
                if e.reader_id in out_readers_ids and presence[0]:
                    presence[1] = e.event_time
                    e.in_or_out = 'out'
                if e.reader_id in out_readers_ids and not presence[
                    0] and previous_attendance_id:  # update last att record
                    in_zone = att_zone_ids.filtered(lambda z: e.door_id in z.door_ids)
                    if in_zone.overwrite_check_out and (
                            e.event_time - previous_attendance_id.check_out) < timedelta(hours=8):
                            # e.event_time - previous_attendance_id.check_out) < relativedelta(hours=8):
                        previous_attendance_id.check_out = e.event_time
                        e.in_or_out = 'out'
                        # previous_attendance_id._compute_times()
                if all(presence):
                    previous_attendance_id = self.env['hr.attendance'].with_context(no_validity_check=True).create({
                        'check_in': presence[0],
                        'check_out': presence[1],
                        'employee_id': employee_id.id,
                    })
                    # previous_attendance_id._compute_times()
                    presence = [None, None]
                previous_event_id = e

            # last one may be opened
            if presence[0] and not presence[1]:
                self.env['hr.attendance'].create({
                    'check_in': presence[0],
                    'in_zone_id': in_zone and in_zone.id,
                    'employee_id': employee_id.id,
                })

            # Check and store open attendance records or bypass attendance constrains
            # Clear old attendance records for the period
            # Search all events based on zone
            # Create all attendance records

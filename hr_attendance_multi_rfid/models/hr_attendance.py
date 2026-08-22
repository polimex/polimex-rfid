from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


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
    )
    # Every attendance the RFID machinery creates is stamped 'rfid', so a
    # rebuild can tell its own records from what a person typed in by hand
    # (manual/kiosk/systray). On uninstall the records fall back to the
    # field's default ('manual') rather than being deleted.
    in_mode = fields.Selection(
        selection_add=[('rfid', "RFID")],
        ondelete={'rfid': 'set default'},
    )

    def write(self, vals):
        for att in self:
            if vals.get('check_out', False) and not att.check_out and att.in_zone_id:
                if self.env.context.get('from_event', None) is None:
                    att.in_zone_id.person_left(att.employee_id)
                vals['in_zone_id'] = False
        return super(HrAttendance, self).write(vals)

    def _get_zone_settings(self):
        """Auto-close settings of the zone THIS attendance was opened in.

        The zone is read from the record's own in_zone_id - the zone the
        session belongs to - never from employee_id.in_zone_ids, which says
        where the person is NOW. A person who already left the zone has
        nothing there, which made their forgotten open attendance impossible
        to close.

        :return: (max_time_in_zone, auto_close_time_for_zone) of the
                 session's zone, or (False, False) when the record carries no
                 attendance zone or the zone sets no limit
                 (max_time_in_zone == 0).
        """
        self.ensure_one()
        zone = self.in_zone_id
        if not zone or not zone.attendance:
            return False, False
        if float_compare(zone.max_time_in_zone, 0.0, precision_digits=2) <= 0:
            return False, False
        return zone.max_time_in_zone, zone.auto_close_time_for_zone

    def needs_autoclose(self):
        """Whether this open attendance has outstayed its zone's limit.

        True only for an open record whose zone limits the stay
        (max_time_in_zone > 0) and whose check-in is older than that limit.
        Records without a zone are never closed by the zone machinery.
        """
        self.ensure_one()
        if self.check_out:
            return False
        max_time, _autoclose = self._get_zone_settings()
        if not max_time:
            return False
        open_worked_hours = (fields.Datetime.now() - self.check_in).total_seconds() / 3600.0
        return float_compare(open_worked_hours, max_time, precision_digits=2) > 0

    def autoclose_attendance(self):
        """Close a forgotten attendance with the hours the zone promises.

        check_out = check_in + auto_close_time_for_zone; when the zone does
        not set Auto-close Worked Hours (0/empty), max_time_in_zone is used
        instead - exactly what the zone's field help promises.
        """
        self.ensure_one()
        max_time, autoclose = self._get_zone_settings()
        if not max_time:
            return
        if float_compare(autoclose or 0.0, 0.0, precision_digits=2) > 0:
            hours = autoclose
        else:
            hours = max_time
        # Stamped with core's own "Automatic Check-Out" mode: the operator's
        # existing filter (hr_attendance_view.xml, "Automatically Checked-Out")
        # then lists these for free, and a record closed by the zone rule is
        # never mistaken for a person's real badge-out. Core's calendar-based
        # cron and this zone sweep work the same pool of open records - either
        # may close first, the other then finds check_out set and moves on.
        self.write({
            'check_out': self.check_in + timedelta(hours=hours),
            'out_mode': 'auto_check_out',
        })

    @api.model
    def check_for_incomplete_attendances(self):
        """Close every forgotten open attendance whose zone limit has passed.

        Run by the scheduled task. Only records carrying a zone can be
        measured against a zone limit, so only those are read; whether the
        limit has passed still depends on each zone's own settings.
        """
        stale_attendances = self.search([
            ('check_out', '=', False),
            ('in_zone_id', '!=', False),
        ])
        for att in stale_attendances.filtered(lambda a: a.needs_autoclose()):
            att.autoclose_attendance()

    # bypass validity if old events processed
    def _check_validity(self):
        if self.env.context.get('no_validity_check', None) is None:
            super(HrAttendance, self)._check_validity()

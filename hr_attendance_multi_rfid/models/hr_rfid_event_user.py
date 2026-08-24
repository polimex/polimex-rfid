# -*- coding: utf-8 -*-
from odoo import fields, models, _


class HrRfidUserEvent(models.Model):
    _name = "hr.rfid.event.user"
    _inherit = "hr.rfid.event.user"

    in_or_out = fields.Selection(
        selection=[ ('in', 'Check In'), ('out', 'Check Out'), ('no_info', 'No Info') ],
        help="""Indicates whether this RFID event was processed as attendance check-in or check-out.

• Check In: Employee entered an attendance zone
• Check Out: Employee left an attendance zone  
• No Info: Event not processed for attendance (may be non-attendance zone or error)

This field is automatically set when recalculating attendance from RFID events.""",
        string='Attendance',
        default='no_info',
    )

    # A granted passage that changes no attendance used to leave nothing
    # behind: the list showed "No Info" and the operator had no way to tell an
    # ordinary second badge from a misconfigured zone. Every place that decides
    # not to touch attendance now says so here, in the operator's words.
    no_attendance_reason = fields.Selection(
        selection=[
            ('already_inside', 'Already inside'),
            ('not_tracked_here', 'Not tracked in this zone'),
            ('nothing_to_close', 'Nothing open to close'),
            ('manual_record', 'Covered by a manual record'),
            ('superseded', 'Replaced by a later entry'),
            ('direction_unknown', 'Direction unknown'),
        ],
        string='Why Not Counted',
        help="Filled in when a granted passage did not change the attendance, so the reason is visible "
             "instead of a blank Attendance column:\n\n"
             "• Already inside: the person was already checked in and this zone keeps the first entry.\n"
             "• Not tracked in this zone: the zone follows only certain departments or tags, and this "
             "person is not one of them.\n"
             "• Nothing open to close: an exit arrived with no attendance open, and this zone does not "
             "reopen the previous one.\n"
             "• Covered by a manual record: the moment already falls inside attendance entered by hand, "
             "which is never overwritten.\n"
             "• Replaced by a later entry: a second entry came before any exit, and the zone keeps the "
             "later one.\n"
             "• Direction unknown: the passage carries no reader, or one that is set to neither In nor "
             "Out, so it cannot be read as an arrival or a departure.",
    )

    def _mark_attendance(self, direction):
        """This passage IS the check-in / check-out.

        Paired with _mark_no_attendance so the two columns can never contradict
        each other: an event that counts carries no reason, and an event that
        carries a reason never claims to have counted. A rebuild that turns a
        discarded passage into a real one clears the old reason by going
        through here.
        """
        if not self:
            return
        self.write({'in_or_out': direction, 'no_attendance_reason': False})

    def _mark_no_attendance(self, reason):
        """Say why this passage left the attendance untouched - LIVE.

        Only a passage that still counts for nothing is given a reason. A door
        can belong to several zones and they are answered one after another,
        so a zone that does not track this person must not undo what another
        zone recorded a moment earlier, whichever order the two come in.

        Takes the empty recordset (and a bare False, which the live path
        passes when it acts on its own clock rather than on an event), so
        callers stay free of guards.
        """
        self.filtered(lambda e: e.in_or_out in (False, 'no_info')) \
            ._write_no_attendance(reason)

    def _rewrite_no_attendance(self, reason):
        """Say why this passage left the attendance untouched - REBUILD.

        The rebuild replays the whole period from the door events, so its
        answer REPLACES any earlier one: a passage that counted last time and
        does not count now must stop claiming to be a check-in. Which is why
        the two engines have a method each instead of one method and a flag -
        forgetting the flag would have looked like nothing at all.
        """
        self._write_no_attendance(reason)

    def _write_no_attendance(self, reason):
        """Shared by the two above; tolerates the empty recordset."""
        if not self:
            return
        self.write({'in_or_out': 'no_info', 'no_attendance_reason': reason})

    def button_show_employee_att_events(self):
        self.ensure_one()
        return {
            'name': _('Attendance for {}').format(self.employee_id.name),
            'view_mode': 'list,form',
            'res_model': 'hr.attendance',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

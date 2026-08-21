from odoo import Command, fields, models, api
from odoo.exceptions import RedirectWarning, UserError
from datetime import timedelta


class WizardHrRecalcAttendanceEmployee(models.TransientModel):
    _name = 'hr.attendance.recalc.wizard'
    _description = 'Wizard for re-create attendance records based on RFID events'

    def _get_default_employees(self):
        if self.env.context.get('active_model') == 'hr.attendance.extra':
            return [self.env['hr.attendance.extra'].browse(self.env.context.get('active_id')).employee_id.id]
        else:
            return []

    def _get_default_from(self):
        if self.env.context.get('active_model') == 'hr.attendance.extra':
            return self.env['hr.attendance.extra'].browse(self.env.context.get('active_id')).for_date
        else:
            return fields.Date.today() - timedelta(days=30)

    def _get_default_to(self):
        if self.env.context.get('active_model') == 'hr.attendance.extra':
            return self.env['hr.attendance.extra'].browse(self.env.context.get('active_id')).for_date
        else:
            return fields.Date.today()

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        required=True,
        string="Employees",
        # default=lambda self: self._get_default_employees(),
        help="""Select employees whose attendance records will be recalculated from RFID events.
        
• Process: Existing auto-generated attendance will be deleted and recreated
• Manual attendance: Records created manually by HR will be preserved
• RFID events: System will analyze all RFID door events to rebuild attendance

Use this when attendance data seems incorrect or after changing zone settings.""",
    )
    start_date = fields.Date(
        string='Start Date',
        default=lambda self: self._get_default_from(),
        help="Starting date for attendance recalculation. Only attendance records from this "
             "date forward will be processed. Default is 30 days ago to cover recent period."
    )
    end_date = fields.Date(
        string='End Date',
        default=lambda self: self._get_default_to(),
        help="Ending date for attendance recalculation. Attendance records will be processed "
             "up to and including this date. Default is today."
    )

    def execute(self):
        """Record the request and hand the screen back.

        Rebuilding is deleting and replaying a period of attendance for every
        person selected. Doing that here would keep the operator waiting until
        the request is cut off, leaving attendance half rebuilt - so the work
        is written down and done in the background, one person at a time.
        Core makes the same move for batch invoice sending
        (odoo/addons/account/wizard/account_move_send_batch_wizard.py:88-119).
        """
        self.ensure_one()
        # Asked here as well as in the rebuild itself, so anybody who may not
        # be rebuilt is named on the screen the operator is looking at, rather
        # than in a report they have to go and find later.
        self.employee_ids._check_recalc_allowed(self.start_date, self.end_date)
        self._check_background_worker_available()

        run = self.env['hr.attendance.recalc.run'].create({
            'employee_ids': [Command.set(self.employee_ids.ids)],
            'date_from': self.start_date,
            'date_to': self.end_date,
        })
        run.action_start()

        watch_it = {
            'type': 'ir.actions.act_window',
            'name': self.env._("Attendance Rebuilds"),
            'res_model': 'hr.attendance.recalc.run',
            'res_id': run.id,
            'view_mode': 'form',
            # 'views' spelled out, not left to 'view_mode'. The server fills it
            # in for the action a button RETURNS (web/controllers/utils.py:23-26
            # calls generate_views), but this one travels inside another
            # action's params, where nothing walks in to complete it. The
            # client then does action.views.map(...) unconditionally
            # (web/static/src/webclient/actions/action_service.js:442) and the
            # whole screen dies with "Cannot read properties of undefined".
            # Core spells it out in the same position - see
            # mass_mailing/wizard/mailing_contact_import.py:114-115.
            'views': [(False, 'form')],
            'target': 'current',
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': self.env._("Rebuilding attendance"),
                'message': self.env._(
                    "Attendance for %(count)s person(s) is being rebuilt in "
                    "the background. You can carry on working - this page "
                    "shows how far it has got.",
                    count=len(self.employee_ids),
                ),
                # Lands the operator on the record that shows the progress -
                # core chains a follow-up action the same way
                # (odoo/addons/mass_mailing/wizard/mailing_contact_to_list.py:53).
                'next': watch_it,
            },
        }

    def _check_background_worker_available(self):
        """Refuse rather than accept a request nothing will ever pick up.

        A scheduled job that has been switched off is never run, not even when
        something asks for it: the trigger is dropped without a word
        (odoo/odoo/addons/base/models/ir_cron.py:774-776). The rebuild would
        sit there looking queued forever.
        """
        cron = self.env.ref(
            'hr_attendance_multi_rfid.hr_attendance_multi_rfid_recalc_cron',
            raise_if_not_found=False,
        )
        if cron and cron.sudo().active:
            return
        if cron and self.env.user.has_group('base.group_system'):
            raise RedirectWarning(
                self.env._(
                    "Attendance cannot be rebuilt right now: the scheduled "
                    "task that does the work is switched off. Switch it back "
                    "on and try again."),
                {
                    'type': 'ir.actions.act_window',
                    'res_model': 'ir.cron',
                    'res_id': cron.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                },
                self.env._("Open the scheduled task"),
            )
        raise UserError(
            self.env._(
                "Attendance cannot be rebuilt right now: the scheduled task "
                "that does the work is switched off. Please ask your system "
                "administrator to switch it back on.")
        )

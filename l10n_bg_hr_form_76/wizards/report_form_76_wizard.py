from odoo import fields, models, _
from odoo.exceptions import UserError


class WizardHrForm76(models.TransientModel):
    _name = 'hr.attendance.form76.wizard'
    _description = 'Wizard for generation Form 76 in Bulgaria'

    department_ids = fields.Many2many(
        comodel_name="hr.department",
        required=True,
        string="Departments",
        help="Generate report for this Department/s",
    )
    report_year = fields.Integer(
        "Calendar Year",
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    report_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], default=lambda self: str(fields.Date.today().month), required=True)
    precision = fields.Integer(
        default=0,
        required=True,
        help='Round the hours to exact precision. Precision=2 (0.00) means 2 digits after decimal point.',
    )
    set_hours_to = fields.Integer(
        default=0,
        required=True,
        help="Replace hours with this hours. \n"
             "This operation will replace real hours per day with this value!\n"
             "0 means do not change the real hours",
    )

    def _prepare_report_data(self):
        """Prepare data dict for report rendering."""
        self.ensure_one()
        current_year = fields.Date.today().year
        if self.report_year < 2020 or self.report_year > current_year:
            raise UserError(_('The year is not valid %d') % self.report_year)

        return {
            'report_year': int(self.report_year),
            'report_month': int(self.report_month),
            'department_ids': self.department_ids.ids,
            'set_hours_to': self.set_hours_to,
            'precision': self.precision,
            'company_id': self.env.company.id,
        }

    def report_print(self):
        data = self._prepare_report_data()
        report = self.env.ref('l10n_bg_hr_form_76.form_76_report')
        return report.report_action(None, data=data)

    def report_view(self):
        data = self._prepare_report_data()
        report = self.env.ref('l10n_bg_hr_form_76.form_76_report')
        result = report.report_action(None, data=data)
        result['report_type'] = 'qweb-html'
        return result

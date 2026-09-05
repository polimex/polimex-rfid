from odoo import api, fields, models


class HwImportOptionsWiz(models.TransientModel):
    _name = 'hr.rfid.hw.import.options.wiz'
    _description = 'Import into this system'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade',
                             help="The survey to import.")
    company_id = fields.Many2one(related='run_id.company_id',
                                 help="The company the records are created for; the department must belong to it.")
    import_hardware = fields.Boolean(default=True, help="Create the modules, controllers, doors and readers. "
                                                        "Without them, no rights can be created either.")
    import_schedules = fields.Boolean(default=True, help="Take the time schedules from the controllers.")
    import_people = fields.Boolean(default=True, help="Create the card holders. Without them, no cards are created.")
    import_cards = fields.Boolean(default=True, help="Create the cards.")
    import_groups = fields.Boolean(default=True, help="Create the access groups and give them to the people.")
    placeholder_owner_type = fields.Selection(string="Create generated holders as", selection=[('contact', 'Contact'), ('employee', 'Employee')],
                                              required=True, default='contact',
                                              help="Kind of record for the generated card holders that were not changed by hand.")
    default_department_id = fields.Many2one('hr.department', string="Department for employees", help="Department for the people imported as employees.")
    employee_count = fields.Integer(string="Employees", compute='_compute_summary', help="People the import will create or reuse as employees; each needs the department below.")
    contact_count = fields.Integer(string="Contacts", compute='_compute_summary', help="People the import will create or reuse as contacts.")
    blocker_count = fields.Integer(string="Must be resolved", compute='_compute_summary', help="Findings that stop the import; 0 means it can start.")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        run = self.env['hr.rfid.hw.import.run'].browse(values.get('run_id') or self.env.context.get('default_run_id'))
        if run:
            values.update({
                'import_hardware': run.import_hardware, 'import_schedules': run.import_schedules,
                'import_people': run.import_people, 'import_cards': run.import_cards,
                'import_groups': run.import_groups, 'placeholder_owner_type': run.placeholder_owner_type,
                'default_department_id': run.default_department_id.id,
            })
        return values

    @api.depends('run_id', 'placeholder_owner_type', 'run_id.person_ids.owner_type', 'run_id.person_ids.include')
    def _compute_summary(self):
        for wiz in self:
            people = wiz.run_id.person_ids.filtered('include')
            # Generated holders the operator has not changed follow the choice
            # made here, so the figures show what the import will do.
            run_default = wiz.run_id.placeholder_owner_type
            employees = 0
            for person in people:
                owner_type = person.owner_type
                if person.source == 'placeholder' and owner_type == run_default:
                    owner_type = wiz.placeholder_owner_type
                if owner_type == 'employee':
                    employees += 1
            wiz.employee_count = employees
            wiz.contact_count = len(people) - employees
            wiz.blocker_count = wiz.run_id.blocker_count

    def action_start(self):
        self.ensure_one()
        self.run_id.write({
            'import_hardware': self.import_hardware, 'import_schedules': self.import_schedules,
            'import_people': self.import_people, 'import_cards': self.import_cards,
            'import_groups': self.import_groups, 'placeholder_owner_type': self.placeholder_owner_type,
            'default_department_id': self.default_department_id.id,
        })
        self.run_id.action_start_import()
        return {'type': 'ir.actions.act_window_close'}

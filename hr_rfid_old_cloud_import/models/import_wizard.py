# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _
import logging

import json

import json

_logger = logging.getLogger(__name__)


class OldCloudImportusers(models.TransientModel):
    _name = 'hr.rfid.old.cloud.import.users'
    _description = 'Old Cloud Import Users'

    do_import = fields.Boolean(default=False)
    import_as = fields.Selection(
        [('contact', 'Contact'), ('employee', 'Employee')],
        default='contact'
    )
    u_id = fields.Integer(string='Internal ID')
    u_code = fields.Char(string='User code')
    u_name = fields.Char(string='User name')
    u_fname = fields.Char(string='First Name')
    u_sname = fields.Char(string='Second Name')
    u_lname = fields.Char(string='Last Name')
    d_id = fields.Integer(string='Department ID')
    d_name = fields.Char(string='Department Name')
    c_id = fields.Integer(string='Company ID')
    c_name = fields.Char(string='Company Name')
    json_data = fields.Char(string='Json Data')
    import_id = fields.Many2one(
        comodel_name='hr.rfid.old.cloud.import.wiz'
    )

    @api.onchange('import_as')
    def _import_as_onchange(self):
        for u in self:
            u.do_import = True

    def get_full_name(self):
        self.ensure_one()
        return (f"{self.u_fname or ''} {self.u_sname or ''} {self.u_lname or ''}").strip()

    def get_record_for_note(self):
        self.ensure_one()
        return (
            f"User Code: {self.u_code or ''} User Name:{self.u_name or ''} Department:{self.d_name or ''} Company:{self.c_name or ''}").strip()

    def import_row(self):
        print(self.u_fname)


class OldCloudImportWiz(models.TransientModel):
    _name = 'hr.rfid.old.cloud.import.wiz'
    _inherit = ['hr.rfid.old.cloud.welcome.wiz', 'balloon.mixin']
    _description = 'Import'

    # company_list = fields.Selection(selection=lambda self: self.get_context_list('company_dict'))
    def _default_department(self):
        dep_id = self.env['hr.department'].with_company(self.env.company).search([], limit=1)
        return dep_id and dep_id.id or None

    default_department = fields.Many2one(
        comodel_name='hr.department',
        default=_default_department,
        help='Use this department if Employee have no Company and Department',
    )
    force_default_department = fields.Boolean(
        default=False,
        help='Force use only this department for selected import',
    )

    default_company = fields.Many2one(
        comodel_name='res.partner',
        default=lambda self: self.env['res.partner'].search([('is_company', '=', True)])[0].id,
        domain=[('is_company', '=', True)],
        help='Use this company if Contact have no Company and Department',
    )
    force_default_company = fields.Boolean(
        default=False,
        help='Force use only this company for selected import',
    )

    users_ids = fields.One2many(
        comodel_name='hr.rfid.old.cloud.import.users',
        inverse_name='import_id'
    )

    import_as = fields.Selection(
        [('contact', 'Contacts'), ('employee', 'Employees')],
        default='employee',
    )

    select_all = fields.Boolean(default=False)

    user_data = fields.Char()

    @api.onchange('import_as')
    def _import_as_on_change(self):
        # self.users_ids.import_as = self.import_as
        self.users_ids.write({'import_as': self.import_as})

    @api.onchange('select_all')
    def _select_all_on_change(self):
        # self.users_ids.do_import = self.select_all
        self.users_ids.write({'do_import': self.select_all})

    def go_back(self):
        return self.env.ref('hr_rfid_old_cloud_import.old_cloud_welcome_wizard_action').read()[0]

    @api.model
    def default_get(self, fields_list):
        res = super(OldCloudImportWiz, self).default_get(fields_list)
        defs = self.env.context.get('defs', {})
        default_import_as = defs['default_import_as']
        defs = {k: v for k, v in defs.items() if k in fields_list}
        # defs = {'default_%s' % k: v for k, v in defs.items() if k in self._fields.keys()}

        res.update(defs)
        if 'users_ids' in fields_list:
            users = self._holders(domain=self.env.context.get('defs', {})['url_domain'],
                                  token=self.env.context.get('defs', {})['url_token'])
            res['default_user_data'] = json.dumps(users)
            existing_user = self.sudo().env['ir.model.data'].search([
                ('module', '=', '__export__'),
                ('name', 'like', 'old_cloud_u_id_')
            ])
            existing_user_ids = [int(l[15:]) for l in existing_user.mapped('name')]
            users = list(filter(lambda u: (u['id'] not in existing_user_ids), users))
            user_ids = self.env['hr.rfid.old.cloud.import.users'].create(
                [self.get_user_data_as_dict(user, self.id, default_import_as) for user in users]
            )
            # users_lines =user_ids.mapped('id')
            users_lines = [(6, 0, user_ids.mapped('id'))]
            # users_lines = [(5,0,0)] + [(0,0,self.get_user_data_as_dict(user, self.id)) for user in users]

            res['users_ids'] = users_lines
        return res

    @api.model
    def get_context_list(self, field):
        select = self.env.context.get('defs', {})
        if field in select.keys() and select[field]:
            return select[field]
        return []

    @api.model
    def get_user_data_as_dict(self, u_data, import_id, import_as):
        return {
            'u_id': u_data['id'],
            'u_code': u_data['hcode'],
            'u_name': u_data['fname'],
            'u_fname': u_data['fname'],
            'u_sname': u_data['mname'],
            'u_lname': u_data['lname'],
            'd_id': u_data['department_id'],
            'd_name': u_data['departments'][0]['name'],
            'c_id': u_data['departments'][0]['customer_id'],
            'c_name': 'Customer %d' % u_data['departments'][0]['customer_id'],
            'import_id': import_id,
            'import_as': import_as,
            'json_data': json.dumps(u_data),
        }

    @api.returns('res.partner')
    def create_res_partner_company(self, user_id):
        company_id = self.env.ref(f'__export__.old_cloud_c_id_{user_id.c_id}', raise_if_not_found=False)
        if not company_id:
            company_id = self.env['res.partner'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.c_name,
                'is_company': True,
            }])
            self.sudo().env['ir.model.data'].create({
                'model': 'res.partner',
                'res_id': company_id.id,
                'module': '__export__',
                'name': 'old_cloud_c_id_%d' % user_id.c_id,
            })
            company_id.message_post(
                body=_('Imported from %s Access Control System') % self._cloud_url()
            )
        return company_id

    @api.returns('res.partner')
    def create_res_partner(self, user_id):
        if self.force_default_company:
            parent_id = self.default_company
        elif user_id.c_id or user_id.d_id:
            parent_id = self.create_res_partner_company(user_id)
        else:
            parent_id = self.default_company

        partner_id = self.env.ref(f'__export__.old_cloud_u_id_{user_id.u_id}', raise_if_not_found=False)
        if not partner_id:
            partner_id = self.env['res.partner'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.get_full_name(),
                # 'is_company': False,
                'parent_id': parent_id and parent_id.id or None,
                'type': 'contact',
                'comment': user_id.get_record_for_note()
            }])
            self.sudo().env['ir.model.data'].create({
                'model': 'res.partner',
                'res_id': partner_id.id,
                'module': '__export__',
                'name': 'old_cloud_u_id_%d' % user_id.u_id,
            })
            partner_id.message_post(
                body=_('Imported from %s Access Control System') % self._cloud_url()
            )
        if partner_id:
            self.create_tags(user_id=user_id, partner_id=partner_id)
            self.create_user_ag_relation(user_id=user_id, partner_id=partner_id)
        return partner_id

    @api.returns('hr.department')
    def create_department(self, d_id, d_name):
        department_id = self.env.ref(f'__export__.old_cloud_d_id_{d_id}', raise_if_not_found=False)
        if not department_id:
            department_id = self.env['hr.department'].with_context({'mail_create_nolog': True}).create([{
                'name': d_name,
            }])
            self.sudo().env['ir.model.data'].create({
                'model': 'hr.department',
                'res_id': department_id.id,
                'module': '__export__',
                'name': 'old_cloud_d_id_%d' % d_id,
            })
            department_id.message_post(
                body=_('Imported from %s Access Control System') % self._cloud_url()
            )
        return department_id

    @api.returns('hr.employee')
    def create_employee(self, user_id, department_id):
        employee = self.env.ref(f'__export__.old_cloud_u_id_{user_id.u_id}', raise_if_not_found=False)
        if not employee:
            employee = self.env['hr.employee'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.get_full_name(),
                'identification_id': user_id.u_code,
                'department_id': department_id and department_id.id or None,
            }])
            self.sudo().env['ir.model.data'].create({
                'model': 'hr.employee',
                'res_id': employee.id,
                'module': '__export__',
                'name': 'old_cloud_u_id_%d' % user_id.u_id,
            })
            employee.message_post(
                body=_('Imported from %s Access Control System') % self._cloud_url()
            )
        return employee

    @api.returns('hr.rfid.card')
    def create_tags(self, user_id, employee_id=None, partner_id=None):
        tags = json.loads(user_id.json_data)['tags']
        for tag in tags:
            card_id = self.env.ref('__export__.old_cloud_tag_id_%d' % tag['id'], raise_if_not_found=False)
            if not card_id:
                card_dict = {
                    'number': tag['number'],
                    # 'card_reference': user_id.u_code,
                    'active': True,
                }
                if employee_id:
                    card_dict.update({'employee_id': employee_id.id})
                elif partner_id:
                    card_dict.update({'contact_id': partner_id.id})
                else:
                    raise exceptions.ValidationError(
                        _('Tag have no employee or contact. Something is wrong with data. Check the log'))
                card_id = self.env['hr.rfid.card'].with_context({'mail_create_nolog': True}).create([card_dict])
                self.sudo().env['ir.model.data'].create({
                    'model': 'hr.rfid.card',
                    'res_id': card_id.id,
                    'module': '__export__',
                    'name': 'old_cloud_tag_id_%d' % tag['id'],
                })
                card_id.message_post(
                    body=_('Imported from %s Access Control System') % self._cloud_url()
                )
        return employee_id and employee_id.hr_rfid_card_ids or partner_id and partner_id.hr_rfid_card_ids

    def create_user_ag_relation(self, user_id, employee_id=None, partner_id=None):
        if not employee_id and not partner_id:
            raise exceptions.ValidationError(_('Missing data: Partner AND Employee'))

        ag_users = json.loads(user_id.json_data)['access_groups']
        for ag in ag_users:
            access_group_id = self.env.ref('__export__.old_cloud_ag_id_%d' % ag['id'], raise_if_not_found=False)
            if not access_group_id:
                _logger.info('Ignoring old cloud access group %s' % ag['name'])
                continue
            if employee_id:
                if not employee_id.department_id.hr_rfid_default_access_group:
                    dummy_ag_id = self.env['hr.rfid.access.group'].create([{'name': 'Dummy default group %d' % ag['id']}])
                    employee_id.department_id.write({
                        'hr_rfid_default_access_group': dummy_ag_id.id,
                        'hr_rfid_allowed_access_groups': [(4, dummy_ag_id.id, 0)]
                    })
                if access_group_id not in employee_id.department_id.hr_rfid_allowed_access_groups:
                    employee_id.department_id.write({
                        'hr_rfid_allowed_access_groups': [(4, access_group_id.id, 0)]
                    })
                employee_id.write({
                    'hr_rfid_access_group_ids': [(0, 0, {
                        'access_group_id': access_group_id.id,
                        'employee_id': employee_id.id,
                        'activate_on': ag['pivot']['start'] or fields.Datetime.now(),
                        'expiration': ag['pivot']['end']
                    })]
                })
            elif partner_id:
                partner_id.write({
                    'hr_rfid_access_group_ids': [(0, 0, {
                        'access_group_id': access_group_id.id,
                        'contact_id': partner_id.id,
                        'activate_on': ag['pivot']['start'] or fields.Datetime.now(),
                        'expiration': ag['pivot']['end']
                    })]
                })

    def do_import_user_as_employee(self, user_id):
        if self.force_default_department:
            department_id = self.default_department
        elif (user_id.c_id or user_id.d_id):
            department_id = self.create_department(user_id.d_id, f'{user_id.c_name}/{user_id.d_name}')
        else:
            department_id = self.default_department
        employee_name = user_id.get_full_name()
        employee_id = self.create_employee(user_id, department_id)
        self.create_tags(user_id=user_id, employee_id=employee_id)
        self.create_user_ag_relation(user_id=user_id, employee_id=employee_id)
        return employee_id

    def do_import_user_as_contact(self, user_id):
        return self.create_res_partner(user_id)
        # c_id = None if user_id.import_as == 'contact' else user_id.c_id
        # d_id = None if user_id.import_as == 'contact' else user_id.d_id
        # department_id = None
        # if c_id:
        #     partner_id = self.create_res_partner(c_id, f'{user_id.c_name}/{user_id.d_name}', is_company=True)
        # partner_name = f"{user_id.u_fname} {user_id.u_sname} {user_id.u_lname} ({user_id.u_name or ''})"
        # partner_id = self.create_employee(user_id.u_id, user_id.u_code, employee_name, department_id)
        # self.create_employee_tags(employee_id, user_id.u_id)
        # return employee_id

    def import_ags(self):
        ags = self._access_groups(self.get_context_list('url_domain'), self.get_context_list('url_token'))
        for ag in ags:
            nag = self.env.ref('__export__.old_cloud_ag_id_%d' % ag['id'], raise_if_not_found=False)
            if not nag:
                nag = self.env['hr.rfid.access.group'].with_context({'mail_create_nolog': True}).create([{
                    'name': ag['name']
                }])
                self.sudo().env['ir.model.data'].create({
                    'model': 'hr.rfid.access.group',
                    'res_id': nag.id,
                    'module': '__export__',
                    'name': 'old_cloud_ag_id_%d' % ag['id'],
                })
                nag.message_post(
                    subject=_('Imported from Old Cloud Access Control System'),
                    body=_("Existing doors in Old Cloud: %s", 'See in the old system!')
                )
        return _('Imported %d Access groups from %s ') % (len(ags), self._cloud_url())

    def import_u(self, selected=False):
        imported_user_count = 0
        user_ids = self.users_ids if not selected else self.users_ids.filtered(lambda u: u.do_import)
        for index, user in enumerate(user_ids):
            # --------------------------------------------
            #             if index > 10:
            #                 continue
            # --------------------------------------------
            # user = self.get_user_data_as_dict(u)
            _logger.info(f'Old Cloud Import: Importing #{index} user with ID: {user.u_id} from {len(self.users_ids)}')
            if user.c_id:  # Company User
                if user.import_as == 'contact':  # Import users with defined company as Contacts
                    # Find or Create Company by Old Cloud ID and Name
                    # Create res.partner with company
                    # Find access group and add to partner with validity
                    # Create hr.rfid.card with partner with expiry from user
                    self.do_import_user_as_contact(user)
                    imported_user_count += 1
                    pass
                if user.import_as == 'employee':  # Import users with defined company as Department with Employees
                    # Find or Create Department by Old Company Company ID and Name
                    # Find access group and add as available in Department
                    # Create employee with this department and access group and validity
                    # Create hr.rfid.card with partner with expiry from user
                    self.do_import_user_as_employee(user)
                    imported_user_count += 1
                    pass
            else:  # Non Company User
                if user.import_as == 'contact':  # Import users without defined company as separate Contacts
                    # Create res.partner as person
                    # Find access group and add to partner with validity
                    # Create hr.rfid.card with partner with expiry from user
                    self.do_import_user_as_contact(user)
                    imported_user_count += 1
                    pass
                if user.import_as == 'employee':  # Import users without defined company as Employees without Department
                    self.do_import_user_as_employee(user)
                    imported_user_count += 1
        return _('Imported %d from %d users from %s. ') % (imported_user_count, len(self.users_ids), self._cloud_url())

    def do_import(self):
        final_message = _('The process finish successful! ')
        selected = self.env.context.get('selected', False)
        try:
            if self.import_access_groups:
                final_message += self.import_ags()
            if self.import_users:
                final_message += self.import_u(selected)
        finally:
            self.users_ids.search([('do_import', '=', True)]).unlink()

        do_import_action = self.env.ref('hr_rfid_old_cloud_import.old_cloud_import_wizard_action').read()[0]
        do_import_action['context'] = {"defs": self.env.context.get('defs', {})}
        return do_import_action
        # if selected:
        #     return do_import_action
        # return self.balloon_success(
        #     title=_('Import success'),
        #     message=final_message,
        #     sticky=True
        # )

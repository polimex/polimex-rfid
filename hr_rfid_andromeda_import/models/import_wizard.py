# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _
import fdb
import logging

import json

_logger = logging.getLogger(__name__)

USERS_SQL="""select
            u_id, U_CODE, u_name, u_fname, u_sname, u_lname,D_id, D_NAME, c_id, C_NAME
            from USERS
            left join USER_JOB UJ on USERS.U_ID = UJ.USERS_U_ID
            left join COMPANY C on UJ.COMPANY_C_ID = C.C_ID
            left join COMPANY_DEPARTMENTS CD on UJ.COMPANY_DEPARTMENTS_D_ID = CD.D_ID
            where (u_id > 2) and (u_active = 1)"""
AG_USER_SQL="""select users_u_id, access_groups_ag_id, agu_start_timestamp,
            agu_expire_timestamp, agu_active from AG_USERS
            where agu_active=1 and USERS_U_ID=%d"""

class AndromedaImportusers(models.TransientModel):
    _name = 'hr.rfid.andromeda.import.users'
    _description = 'Andromeda Import Users'

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
    import_id = fields.Many2one(
        comodel_name='hr.rfid.andromeda.import.wiz'
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
        return (f"User Code: {self.u_code or ''} User Name:{self.u_name or ''} Department:{self.d_name or ''} Company:{self.c_name or ''}").strip()

    def import_row(self):
        print(self.u_fname)


class AndromedaImportWiz(models.TransientModel):
    _name = 'hr.rfid.andromeda.import.wiz'
    _inherit = 'hr.rfid.andromeda.welcome.wiz'
    _description = 'Import'

    company_list = fields.Selection(selection=lambda self: self.get_context_list('company_dict'))
    default_department = fields.Many2one(
        comodel_name='hr.department',
        default=lambda self: self.env['hr.department'].search([])[0].id,
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
        comodel_name='hr.rfid.andromeda.import.users',
        inverse_name='import_id'
    )

    import_as = fields.Selection(
        [('contact', 'Contacts'), ('employee', 'Employees')],
        default='employee',
    )

    select_all = fields.Boolean(default=False)

    @api.onchange('import_as')
    def _import_as_on_change(self):
        # self.users_ids.import_as = self.import_as
        self.users_ids.write({'import_as': self.import_as})

    @api.onchange('select_all')
    def _select_all_on_change(self):
        # self.users_ids.do_import = self.select_all
        self.users_ids.write({'do_import': self.select_all})

    def go_back(self):
        return self.env.ref('hr_rfid_andromeda_import.andromeda_welcome_wizard_action').read()[0]


    @api.model
    def default_get(self, fields_list):
        res = super(AndromedaImportWiz, self).default_get(fields_list)
        defs = self.env.context.get('defs', {})
        default_import_as = defs['default_import_as']
        defs = {k: v for k, v in defs.items() if k in fields_list}

        res = defs or res
        if 'users_ids' in fields_list:
            users = self.do_fb_sql_context(USERS_SQL)
            existing_user = self.sudo().env['ir.model.data'].search([
                ('module','=','__export__'),
                ('name','like', 'andromeda_u_id_')
            ])
            existing_user_ids = [int(l[15:]) for l in existing_user.mapped('name')]
            users = list(filter(lambda u: (u[0] not in existing_user_ids), users))
            user_ids = self.env['hr.rfid.andromeda.import.users'].create(
                [self.get_user_data_as_dict(user, self.id, default_import_as) for user in users]
            )
            # users_lines =user_ids.mapped('id')
            users_lines =[(6, 0, user_ids.mapped('id'))]
            # users_lines = [(5,0,0)] + [(0,0,self.get_user_data_as_dict(user, self.id)) for user in users]

            res['users_ids'] = users_lines
        return res

    @api.model
    def get_context_list(self, field):
        select = self.env.context.get('defs', {})
        if select:
            try:
                return json.loads(select[field])
            except:
                return select[field]
        return []

    @api.model
    def get_user_data_as_dict(self, u_data, import_id, import_as):
        return {
            'u_id':u_data[0],
            'u_code':u_data[1],
            'u_name':u_data[2],
            'u_fname':u_data[3],
            'u_sname':u_data[4],
            'u_lname':u_data[5],
            'd_id':u_data[6],
            'd_name':u_data[7],
            'c_id':u_data[8],
            'c_name':u_data[9],
            'import_id':import_id,
            'import_as':import_as,
        }

    @api.returns('res.partner')
    def create_res_partner_company(self, user_id):
        company_id = self.env.ref(f'__export__.andromeda_c_id_{user_id.c_id}', raise_if_not_found=False)
        if not company_id:
            company_id = self.env['res.partner'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.c_name,
                'is_company': True,
            }])
            self.sudo().env['ir.model.data'].create({
                'model': 'res.partner',
                'res_id': company_id.id,
                'module': '__export__',
                'name': f'andromeda_c_id_{user_id.c_id}',
            })
            company_id.message_post(
                body=_('Imported from Andromeda Access Control System')
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

        partner_id = self.env.ref(f'__export__.andromeda_u_id_{user_id.u_id}', raise_if_not_found=False)
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
                'name': f'andromeda_u_id_{user_id.u_id}',
            })
            partner_id.message_post(
                body=_('Imported from Andromeda Access Control System')
            )
        if partner_id:
            self.create_tags(user_id=user_id, partner_id=partner_id)
            self.create_user_ag_relation(user_id=user_id, partner_id=partner_id)
        return partner_id

    @api.returns('hr.department')
    def create_department(self, d_id, d_name):
        department_id = self.env.ref(f'__export__.andromeda_d_id_{d_id}', raise_if_not_found=False)
        if not department_id:
            department_id = self.env['hr.department'].with_context({'mail_create_nolog': True}).create([{
                'name': d_name,
            }])
            self.sudo().env['ir.model.data'].create({
                'model': 'hr.department',
                'res_id': department_id.id,
                'module': '__export__',
                'name': f'andromeda_d_id_{d_id}',
            })
            department_id.message_post(
                body=_('Imported from Andromeda Access Control System')
            )
        return department_id

    @api.returns('hr.employee')
    def create_employee(self, user_id, department_id):
        employee = self.env.ref(f'__export__.andromeda_u_id_{user_id.u_id}', raise_if_not_found=False)
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
                'name': f'andromeda_u_id_{user_id.u_id}',
            })
            employee.message_post(
                body=_('Imported from Andromeda Access Control System \n'
                       'Data from Andromeda: ToDo')
            )
        return employee

    @api.returns('hr.rfid.card')
    def create_tags(self, user_id, employee_id= None, partner_id=None):
        tags = self.do_fb_sql_context(
            f'select tag_id, tag_active, tag_number \
              from USERS_TAGDATA \
              where users_u_id = {user_id.u_id}')
        for tag in tags:
            card_id = self.env.ref(f'__export__.andromeda_tag_id_{tag[0]}', raise_if_not_found=False)
            if not card_id:
                card_dict = {
                    'number': tag[2],
                    'card_reference': user_id.u_code,
                    'active': tag[1] == 1,
                }
                if employee_id:
                    card_dict.update({'employee_id': employee_id.id})
                elif partner_id:
                    card_dict.update({'contact_id': partner_id.id})
                else:
                    raise exceptions.ValidationError(_('Tag have no employee or contact. Something is wrong with data. Check the log'))
                card_id = self.env['hr.rfid.card'].with_context({'mail_create_nolog': True}).create([card_dict])
                self.sudo().env['ir.model.data'].create({
                    'model': 'hr.rfid.card',
                    'res_id': card_id.id,
                    'module': '__export__',
                    'name': f'andromeda_tag_id_{tag[0]}',
                })
                card_id.message_post(
                    body=_('Imported from Andromeda Access Control System')
                )
        return employee_id and employee_id.hr_rfid_card_ids or partner_id and partner_id.hr_rfid_card_ids

    def create_user_ag_relation(self, user_id, employee_id=None, partner_id=None):
        if not employee_id and not partner_id:
            raise exceptions.ValidationError('Missing data: Partner AND Employee')

        ag_users = self.do_fb_sql_context(AG_USER_SQL % user_id.u_id)
        for ag in ag_users:
            access_group_id = self.env.ref(f'__export__.andromeda_ag_id_{ag[1]}', raise_if_not_found=False)
            if not access_group_id:
                _logger.info(f'Ignoring andromeda access group {ag[1]}')
                continue
            if employee_id:
                if not employee_id.department_id.hr_rfid_default_access_group:
                    dummy_ag_id = self.env['hr.rfid.access.group'].create([{'name':f'Dummy default group ({ag[1]})'}])
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
                        'expiration': ag[3]
                    })]
                })
            elif partner_id:
                partner_id.write({
                    'hr_rfid_access_group_ids': [(0, 0, {
                        'access_group_id': access_group_id.id,
                        'contact_id': partner_id.id,
                        'expiration': ag[3]
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
        ags = self.get_context_list('ag_dict')
        for ag in ags:
            nag = self.env.ref(f'__export__.andromeda_ag_id_{ag[0]}', raise_if_not_found=False)
            if not nag:
                nag = self.env['hr.rfid.access.group'].with_context({'mail_create_nolog': True}).create([{
                    'name': ag[1]
                }])
                self.sudo().env['ir.model.data'].create({
                    'model': 'hr.rfid.access.group',
                    'res_id': nag.id,
                    'module': '__export__',
                    'name': f'andromeda_ag_id_{ag[0]}',
                })
                doors = self.do_fb_sql_context(
                    f'select CD_NAME \
                        from CTRLS_DOORS \
                        right join AG_DOORS AD on CTRLS_DOORS.CD_ID = AD.CTRLS_DOORS_CD_ID \
                        where AD.ACCESS_GROUPS_AG_ID = {ag[0]}')
                doors = '; '.join([d[0] for d in doors])
                nag.message_post(
                    subject=_('Imported from Andromeda Access Control System'),
                    body=_("Existing doors in Andromeda: %s", doors)
                )
        return _('Imported %d Access groups from Andromeda. ',len(ags))

    def import_u(self, selected = False):
        imported_user_count = 0
        user_ids = self.users_ids if not selected else self.users_ids.filtered(lambda u: u.do_import)
        for index, user in enumerate(user_ids):
# --------------------------------------------
#             if index > 10:
#                 continue
# --------------------------------------------
# user = self.get_user_data_as_dict(u)
            _logger.info(f'Andromeda Import: Importing #{index} user with ID: {user.u_id} from {len(self.users_ids)}')
            if user.c_id:  # Company User
                if user.import_as == 'contact':  # Import users with defined company as Contacts
                    # Find or Create Company by Andromeda ID and Name
                    # Create res.partner with company
                    # Find access group and add to partner with validity
                    # Create hr.rfid.card with partner with expiry from user
                    self.do_import_user_as_contact(user)
                    imported_user_count += 1
                    pass
                if user.import_as == 'employee':  # Import users with defined company as Department with Employees
                    # Find or Create Department by Andromeda Company ID and Name
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
        return _('Imported %d from %d users from Andromeda. ') % (imported_user_count, len(self.users_ids))

    def do_import(self):
        final_message = _('The process finish successful! ')
        selected = self.env.context.get('selected', False)
        try:
            if self.import_access_groups:
                final_message += self.import_ags()
            if self.import_users:
                final_message += self.import_u(selected)
        finally:
            # self.env['hr.rfid.andromeda.import.users'].search([('do_import','=',True)]).unlink()
            self.users_ids.search([('do_import','=',True)]).unlink()

        do_import_action = self.env.ref('hr_rfid_andromeda_import.andromeda_import_wizard_action').read()[0]
        do_import_action['context'] = {"defs": self.env.context.get('defs', {})}

        return do_import_action
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': _('The Import from Andromeda Finish'),
        #         'message': final_message,
        #         'sticky': True,
        #     }}


    @api.model
    def do_fb_sql_context(self, sql):
        # https://firebirdsql.org/file/documentation/drivers_documentation/python/fdb/getting-started.html
        try:
            con = fdb.connect(
                host=self.get_context_list('ip_address'),
                database=self.get_context_list('database_path'),
                user='sysdba',
                password='masterkey',
                charset='UTF8'
            )
            cur = con.cursor()
            cur.execute(sql)
            res = cur.fetchall()
            con.close()
            return res
        except fdb.DatabaseError as e:
            _logger.warning(e)
            raise exceptions.ValidationError(e)
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

# ir.model.data module every record created by this import is registered under.
# '__import__' is what Odoo core itself writes for imported rows
# (odoo/odoo/orm/models.py:915, BaseModel.load()), so a second run recognises
# what the first run created exactly the way core would.
LEDGER_MODULE = '__import__'

# Identity of the source system inside the external ID. The Firebird connection
# exposes no stable installation identifier (the IP address can change between
# runs and the database path is the same on every default Andromeda install),
# so a single slug is used for every Andromeda source.
SOURCE_SLUG = 'andromeda'

# Source table tokens. USERS and COMPANY both land in res.partner, so the source
# record reference has to say which Andromeda table the id belongs to.
SRC_USER = 'u'
SRC_COMPANY = 'c'
SRC_DEPARTMENT = 'd'
SRC_ACCESS_GROUP = 'ag'
SRC_TAG = 'tag'
SRC_AG_USER = 'agu'
SRC_PLACEHOLDER_AG = 'placeholder'


class AndromedaImportusers(models.TransientModel):
    _name = 'hr.rfid.andromeda.import.users'
    _description = 'Andromeda Import Users'

    do_import = fields.Boolean(
        default=False,
        string='Import This User',
        help="""Select whether to import this specific user.
        
        • When enabled: User will be included in the import process
        • When disabled: User will be skipped during import
        • Bulk control: Use 'Select All' to toggle all users at once
        
        Note: Only selected users will be imported from the Andromeda database.""")
    import_as = fields.Selection(
        [('contact', 'Contact'), ('employee', 'Employee')],
        default='contact',
        string='Import As',
        help="""Choose how to import this user into Odoo.
        
        • Contact: Creates a contact/partner record
        • Employee: Creates an employee record with HR functionality
        • Default: Set by the wizard's global import type
        
        Note: Employee import includes HR features like attendance and access groups."""
    )
    u_id = fields.Integer(
        string='Internal ID',
        help="""Unique user identifier from Andromeda system.
        
        • Source: Andromeda database user ID
        • Purpose: Links imported records back to original system
        • Reference: Used for avoiding duplicate imports
        
        Note: This ID is used to track which users have already been imported.""")
    u_code = fields.Char(
        string='User Code',
        help="""User identification code from Andromeda system.
        
        • Usage: Employee badge number or identification code
        • Import: Becomes employee identification_id or card reference
        • Format: Alphanumeric code unique per user
        
        Note: This code often matches physical RFID card numbers.""")
    u_name = fields.Char(
        string='Username',
        help="""Username from Andromeda access control system.
        
        • Login: Original login name in Andromeda
        • Reference: Used for cross-system identification
        • Display: Shown for administrator reference
        
        Note: May differ from the person's actual name - often a login identifier.""")
    u_fname = fields.Char(
        string='First Name',
        help="First name field from the Andromeda DB. Maps to the Odoo record's structured name.",
    )
    u_sname = fields.Char(
        string='Second Name',
        help="Middle / second name from the Andromeda DB.",
    )
    u_lname = fields.Char(
        string='Last Name',
        help="Last name from the Andromeda DB.",
    )
    d_id = fields.Integer(
        string='Department ID',
        help="Numeric department ID from Andromeda. Translated to a local hr.department through the welcome-wizard mapping.",
    )
    d_name = fields.Char(
        string='Department Name',
        help="Department display name from Andromeda — shown for human cross-check.",
    )
    c_id = fields.Integer(
        string='Company ID',
        help="Numeric company ID from Andromeda. Translated to a local res.company via company_dict.",
    )
    c_name = fields.Char(
        string='Company Name',
        help="Company display name from Andromeda — shown for human cross-check.",
    )
    import_id = fields.Many2one(
        comodel_name='hr.rfid.andromeda.import.wiz',
        help="Parent import-run wizard this user row belongs to. Set automatically when the wizard fetches the user list.",
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
        for row in self:
            _logger.debug('Andromeda import row selected: %s', row.u_fname)


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
        inverse_name='import_id',
        help="Users discovered in the Andromeda DB. Operator picks per-row which ones to import and as what (contact vs employee).",
    )

    import_as = fields.Selection(
        [('contact', 'Contacts'), ('employee', 'Employees')],
        default='employee',
        help="Bulk-applied default for the per-row Import As column. Changing this rewrites every users_ids row.",
    )

    select_all = fields.Boolean(
        default=False,
        help="Master toggle that ticks/un-ticks the do_import flag on every users_ids row.",
    )

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
            existing_user_ids = self._already_imported_user_ids()
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

    # -- Import ledger -----------------------------------------------------
    # Every record this wizard creates is registered with an external ID that
    # names the source system, the target model and the source record. That
    # register is what makes a second run of the same import find what the
    # first run created instead of creating it again.

    def _source_slug(self):
        """Identity of the system this run reads from."""
        return SOURCE_SLUG

    def _xml_id_name(self, model, source_ref):
        """Name part of the external ID of one imported record."""
        return 'rfid_import_%s_%s_%s' % (
            self._source_slug(), model.replace('.', '_'), source_ref,
        )

    def _xml_id(self, model, source_ref):
        return '%s.%s' % (LEDGER_MODULE, self._xml_id_name(model, source_ref))

    def _find_imported(self, model, source_ref):
        """The record a previous run created for this source record, if any."""
        return self.env.ref(
            self._xml_id(model, source_ref), raise_if_not_found=False,
        )

    def _mark_imported(self, record, source_ref):
        """Register a freshly created record against its source record."""
        self.sudo().env['ir.model.data'].create({
            'model': record._name,
            'res_id': record.id,
            'module': LEDGER_MODULE,
            'name': self._xml_id_name(record._name, source_ref),
        })
        return record

    def _already_imported_user_ids(self):
        """Andromeda user ids that a previous run already brought in.

        A user can have landed either as an employee or as a contact, so both
        target models are looked up. Companies also live in res.partner - the
        source table token in the reference keeps them out.
        """
        prefixes = [
            self._xml_id_name(model, '%s_' % SRC_USER)
            for model in ('hr.employee', 'res.partner')
        ]
        domain = ['|'] * (len(prefixes) - 1)
        domain += [('name', '=like', '%s%%' % prefix) for prefix in prefixes]
        imported = self.sudo().env['ir.model.data'].search(
            [('module', '=', LEDGER_MODULE)] + domain,
        )
        user_ids = set()
        for name in imported.mapped('name'):
            for prefix in prefixes:
                if name.startswith(prefix):
                    source_id = name[len(prefix):]
                    if source_id.isdigit():
                        user_ids.add(int(source_id))
                    break
        return user_ids

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

    def create_res_partner_company(self, user_id):
        source_ref = f'{SRC_COMPANY}_{user_id.c_id}'
        company_id = self._find_imported('res.partner', source_ref)
        if not company_id:
            company_id = self.env['res.partner'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.c_name,
                'is_company': True,
            }])
            self._mark_imported(company_id, source_ref)
            company_id.message_post(
                body=_('Imported from Andromeda Access Control System')
            )
        return company_id

    def create_res_partner(self, user_id):
        if self.force_default_company:
            parent_id = self.default_company
        elif user_id.c_id or user_id.d_id:
            parent_id = self.create_res_partner_company(user_id)
        else:
            parent_id = self.default_company

        source_ref = f'{SRC_USER}_{user_id.u_id}'
        partner_id = self._find_imported('res.partner', source_ref)
        if not partner_id:
            partner_id = self.env['res.partner'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.get_full_name(),
                # 'is_company': False,
                'parent_id': parent_id and parent_id.id or None,
                'type': 'contact',
                'comment': user_id.get_record_for_note()
            }])
            self._mark_imported(partner_id, source_ref)
            partner_id.message_post(
                body=_('Imported from Andromeda Access Control System')
            )
        if partner_id:
            self.create_tags(user_id=user_id, partner_id=partner_id)
            self.create_user_ag_relation(user_id=user_id, partner_id=partner_id)
        return partner_id

    def create_department(self, d_id, d_name):
        source_ref = f'{SRC_DEPARTMENT}_{d_id}'
        department_id = self._find_imported('hr.department', source_ref)
        if not department_id:
            department_id = self.env['hr.department'].with_context({'mail_create_nolog': True}).create([{
                'name': d_name,
            }])
            self._mark_imported(department_id, source_ref)
            department_id.message_post(
                body=_('Imported from Andromeda Access Control System')
            )
        return department_id

    def create_employee(self, user_id, department_id):
        source_ref = f'{SRC_USER}_{user_id.u_id}'
        employee = self._find_imported('hr.employee', source_ref)
        if not employee:
            employee = self.env['hr.employee'].with_context({'mail_create_nolog': True}).create([{
                'name': user_id.get_full_name(),
                'identification_id': user_id.u_code,
                'department_id': department_id and department_id.id or None,
            }])
            self._mark_imported(employee, source_ref)
            employee.message_post(
                body=_('Imported from Andromeda Access Control System \n'
                       'Data from Andromeda: ToDo')
            )
        return employee

    def create_tags(self, user_id, employee_id= None, partner_id=None):
        tags = self.do_fb_sql_context(
            f'select tag_id, tag_active, tag_number \
              from USERS_TAGDATA \
              where users_u_id = {user_id.u_id}')
        for tag in tags:
            source_ref = f'{SRC_TAG}_{tag[0]}'
            card_id = self._find_imported('hr.rfid.card', source_ref)
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
                self._mark_imported(card_id, source_ref)
                card_id.message_post(
                    body=_('Imported from Andromeda Access Control System')
                )
        return employee_id and employee_id.hr_rfid_card_ids or partner_id and partner_id.hr_rfid_card_ids

    def _get_placeholder_access_group(self, source_ag_id):
        """Placeholder group a department gets when it has no default one.

        Registered against the source access group that made it necessary, so
        a second run reuses it instead of leaving another one behind.
        """
        source_ref = f'{SRC_PLACEHOLDER_AG}_{source_ag_id}'
        placeholder = self._find_imported('hr.rfid.access.group', source_ref)
        if not placeholder:
            placeholder = self.env['hr.rfid.access.group'].create([{
                'name': f'Dummy default group ({source_ag_id})',
            }])
            self._mark_imported(placeholder, source_ref)
        return placeholder

    def _add_ag_membership(self, user_id, source_ag_id, access_group_id,
                           membership_vals, employee_id=None, partner_id=None):
        """Give one person one access group, once.

        Two guards, on purpose. The external ID is what makes a re-run skip a
        membership this import created. The (person, access group) lookup
        covers memberships made before external IDs were written at all -
        without it the first run after this change would duplicate every one
        of them, because nothing in the database says they came from here.
        """
        if employee_id:
            owner, owner_field = employee_id, 'employee_id'
            rel_model = 'hr.rfid.access.group.employee.rel'
        else:
            owner, owner_field = partner_id, 'contact_id'
            rel_model = 'hr.rfid.access.group.contact.rel'

        source_ref = f'{SRC_AG_USER}_{user_id.u_id}_{source_ag_id}'
        if self._find_imported(rel_model, source_ref):
            return self.env[rel_model]

        already = self.env[rel_model].search([
            (owner_field, '=', owner.id),
            ('access_group_id', '=', access_group_id.id),
        ], limit=1)
        if already:
            _logger.debug(
                'Access group %s is already given to %s - not given again',
                access_group_id.id, owner.display_name,
            )
            return already

        before = owner.hr_rfid_access_group_ids
        owner.write({
            'hr_rfid_access_group_ids': [(0, 0, dict(
                membership_vals,
                access_group_id=access_group_id.id,
                **{owner_field: owner.id},
            ))],
        })
        created = owner.hr_rfid_access_group_ids - before
        if len(created) == 1:
            self._mark_imported(created, source_ref)
        else:
            _logger.warning(
                'Could not register the access group %s given to %s; a later '
                'import run may offer it a second time',
                access_group_id.id, owner.display_name,
            )
        return created

    def create_user_ag_relation(self, user_id, employee_id=None, partner_id=None):
        if not employee_id and not partner_id:
            raise exceptions.ValidationError('Missing data: Partner AND Employee')

        ag_users = self.do_fb_sql_context(AG_USER_SQL % user_id.u_id)
        for ag in ag_users:
            access_group_id = self._find_imported(
                'hr.rfid.access.group', f'{SRC_ACCESS_GROUP}_{ag[1]}',
            )
            if not access_group_id:
                _logger.info(f'Ignoring andromeda access group {ag[1]}')
                continue
            if employee_id:
                if not employee_id.department_id.hr_rfid_default_access_group:
                    dummy_ag_id = self._get_placeholder_access_group(ag[1])
                    employee_id.department_id.write({
                        'hr_rfid_default_access_group': dummy_ag_id.id,
                        'hr_rfid_allowed_access_groups': [(4, dummy_ag_id.id, 0)]
                    })
                if access_group_id not in employee_id.department_id.hr_rfid_allowed_access_groups:
                    employee_id.department_id.write({
                        'hr_rfid_allowed_access_groups': [(4, access_group_id.id, 0)]
                    })
                self._add_ag_membership(
                    user_id, ag[1], access_group_id,
                    {'expiration': ag[3]},
                    employee_id=employee_id,
                )
            elif partner_id:
                self._add_ag_membership(
                    user_id, ag[1], access_group_id,
                    {'expiration': ag[3]},
                    partner_id=partner_id,
                )

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
            source_ref = f'{SRC_ACCESS_GROUP}_{ag[0]}'
            nag = self._find_imported('hr.rfid.access.group', source_ref)
            if not nag:
                nag = self.env['hr.rfid.access.group'].with_context({'mail_create_nolog': True}).create([{
                    'name': ag[1]
                }])
                self._mark_imported(nag, source_ref)
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
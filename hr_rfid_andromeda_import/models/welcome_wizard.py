# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, exceptions, _
import fdb
import logging

_logger = logging.getLogger(__name__)


class AndromedaWelcomeWiz(models.TransientModel):
    _name = 'hr.rfid.andromeda.welcome.wiz'
    _description = 'Andromeda Import Welcome'

    ip_address = fields.Char(
        string='IP address',
        required=True,
        default='192.168.10.89',
        help="IP address of the Windows host running the Andromeda Firebird DB engine. Reachable from this Odoo box on the Firebird port (3050).",
    )
    database_path = fields.Char(
        string='Database Path',
        required=True,
        default='C:\Program Files (x86)\Polimex\Andromeda\Database\Andromeda.fdb',
        help="Absolute path to the Andromeda.fdb file as seen by the Firebird server (Windows path on a Windows host). Default points to a typical install.",
    )

    users_count = fields.Integer(
        default=0,
        help="Number of users discovered in the Andromeda DB after Test Connection - informational, used to size the import.",
    )
    company_dict = fields.Char(
        help="Internal JSON mapping (Andromeda company ID → Odoo res.company ID) populated after Test Connection. Not user-editable.",
    )
    ag_dict = fields.Char(
        help="Internal JSON mapping (Andromeda access group → Odoo hr.rfid.access.group) populated after Test Connection. Not user-editable.",
    )

    connection_checked = fields.Boolean(
        default=False,
        help="True after a successful Firebird login and structural probe. Gates the Import button.",
    )
    default_import_as = fields.Selection(
        [('contact', 'Contacts'), ('employee', 'Employees')],
        default='employee',
        help="Where Andromeda users land in Odoo by default - hr.employee for staff, res.partner for external contacts.",
    )

    import_access_groups = fields.Boolean(
        default=True,
        help="Include Andromeda access groups and their door bindings in the import.",
    )
    import_users = fields.Boolean(
        default=True,
        help="Include Andromeda users (with cards) in the import. Disable to import only structure first.",
    )

    def do_check_connection(self):
        try:
            con = fdb.connect(
                host=self.ip_address,
                database=self.database_path,
                user='sysdba',
                password='masterkey',
                charset='UTF8'
            )
            cur = con.cursor()

            def get_count(table):
                cur.execute(f"select count(*) from {table}")
                res = cur.fetchall()
                return res[0][0]

            def get_companies():
                cur.execute("select c_id,c_name from COMPANY")
                return cur.fetchall()
            def get_ags():
                cur.execute("select ag_id, ag_name from ACCESS_GROUPS")
                return cur.fetchall()


            self.users_count = get_count('USERS')
            self.company_dict = json.dumps(get_companies())
            self.ag_dict = json.dumps(get_ags())
            self.connection_checked = True
            con.close()
            # curr_vals = self.read(list(set(self._fields)))[0]
            curr_vals = self.read(['ip_address',
                                   'database_path',
                                   'users_count',
                                   'company_dict',
                                   'ag_dict',
                                   'connection_checked',
                                   'import_access_groups',
                                   'import_users',
                                   'default_import_as',
                                   ])[0]
            curr_vals.pop('id')
            do_import_action = self.env.ref('hr_rfid_andromeda_import.andromeda_import_wizard_action').read()[0]
            do_import_action['context'] = {"defs": curr_vals}
            return do_import_action
        except fdb.DatabaseError as e:
            _logger.warning(e)
            raise exceptions.ValidationError(e)
        if not con.closed:
            try:
                con.close()
            except:
                pass

        # return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': _('The following replenishment order has been generated'),
        #             'message': '%s',
        #             # 'links': [{
        #             #     'label': production.name,
        #             #     'url': f'#action={action.id}&id={production.id}&model=mrp.production'
        #             # }],
        #             'sticky': False,
        #         }}

        # return {'type': 'ir.actions.client', 'tag': 'reload'}

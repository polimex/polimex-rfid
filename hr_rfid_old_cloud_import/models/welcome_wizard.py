# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, exceptions, _
import requests
import logging

_logger = logging.getLogger(__name__)


class OldCloudWelcomeWiz(models.TransientModel):
    _name = 'hr.rfid.old.cloud.welcome.wiz'
    _description = 'Old Polimex Cloud Import Welcome'

    url_domain = fields.Selection([
        ('pc', 'my.polimex.online'),
        ('ss', 'schoolsafety.online'),
    ], default='pc')
    url_token = fields.Char(
        string='Access token',
        required=True,
        default='v3cTzhBpqDxJ8vIzzT1eR0faBZIvbJVLK1zrCpmpQG70dILeFSPNw1MyNAbzuslxTwWFkCkOincv9luwBcr0sJwXgFFNIdji6Vm76qEgYQi7Slrec9WldyVFiSqpp5AITAM6eJ81EbdNrWrYEGdCKusOizd7mhs9iUimq3t1RKgMue2dXAnnkOwOEt9LEXTiRhEwb1ERlhKBpEZxQRpZWQm56onizQVWk4zIFXMXqrimMj5LpvVz6oQ5fRBfosQ'
    )
    users_count = fields.Integer(
        default=0
    )
    company_dict = fields.Char()
    ag_dict = fields.Char()

    connection_checked = fields.Boolean(default=False)
    default_import_as = fields.Selection(
        [('contact', 'Contacts'), ('employee', 'Employees')],
        default='employee',
    )

    import_hardware = fields.Boolean(default=True)
    import_access_groups = fields.Boolean(default=True)
    import_users = fields.Boolean(default=True)
    import_events = fields.Boolean(default=True)

    def _cloud_url(self, d=None):
        if d is None:
            d = self.url_domain
        if d == 'pc':
            return 'https://api.polimex.online'
        else:
            return 'https://schoolsafety.online'

    def _get(self, path, head=False, domain=None, token=None):
        headers = {
            'Cache-Control': 'no-cache',
            'Accept-Encoding': 'gzip,deflate,br',
            'polimex-token': token or self.url_token
        }
        try:
            if domain is None:
                url = self._cloud_url()
            else:
                url = self._cloud_url(domain)
            if head:
                response = requests.head('%s%s' % (url, path), timeout=5, headers=headers, verify=False)
            else:
                response = requests.get('%s%s' % (url, path), timeout=5, headers=headers, verify=False)
            if response.status_code != 200:
                raise exceptions.ValidationError(_('Error response from %s. %s (%s)') % (
                    '%s%s' % (url, path),
                    response.reason,
                    response.status_code
                ))
            return len(response.content) > 0 and response.json() or {}
        except Exception as e:
            _logger.warning(e)
            raise exceptions.ValidationError(e)

    def _holders(self, domain=None, token=None):
        res = self._get('/v1/holders?include=tags,access_groups,departments', domain=domain, token=token)
        if res:
            return res['data']
        else:
            return []

    def _access_groups(self, domain=None, token=None):
        res = self._get('/v1/access_groups', domain=domain, token=token)
        if res:
            return res['data']
        else:
            return []

    def _chech_connection(self, domain=None, token=None):
        return self._get('/v1/holders?include=tags,access_groups', head=True, domain=domain, token=token)

    def do_check_connection(self):

        try:
            self._chech_connection()
            # def get_count(table):
            #     cur.execute(f"select count(*) from {table}")
            #     res = cur.fetchall()
            #     return res[0][0]
            #
            # def get_companies():
            #     cur.execute("select c_id,c_name from COMPANY")
            #     return cur.fetchall()
            # def get_ags():
            #     cur.execute("select ag_id, ag_name from ACCESS_GROUPS")
            #     return cur.fetchall()

            # self.users_count = get_count('USERS')
            # self.company_dict = json.dumps(get_companies())
            self.company_dict = [('-1', 'Old Cloud Customer')]
            # self.ag_dict = json.dumps(get_ags())
            self.connection_checked = True
            # curr_vals = self.read(list(set(self._fields)))[0]
            curr_vals = self.read(['url_domain',
                                   'url_token',
                                   'users_count',
                                   'company_dict',
                                   'ag_dict',
                                   'connection_checked',
                                   'import_access_groups',
                                   'import_hardware',
                                   'import_events',
                                   'import_users',
                                   'default_import_as',
                                   ])[0]
            curr_vals.pop('id')
            do_import_action = self.env.ref('hr_rfid_old_cloud_import.old_cloud_import_wizard_action').read()[0]
            do_import_action['context'] = {"defs": curr_vals}
            return do_import_action
        except Exception as e:
            _logger.warning(e)
            raise exceptions.ValidationError(e)

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

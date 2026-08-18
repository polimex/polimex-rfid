# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, exceptions, _
import requests
import logging

_logger = logging.getLogger(__name__)


class OldCloudWelcomeWiz(models.TransientModel):
    _name = 'hr.rfid.old.cloud.welcome.wiz'
    _description = 'Old Polimex Cloud Import Welcome'

    url_domain = fields.Selection(
        [
            ('pc', 'my.polimex.online'),
            ('ss', 'schoolsafety.online'),
        ],
        default='pc',
        help="Which legacy cloud to import from - the public Polimex cloud or the School Safety variant. Determines the API base URL used by the wizard.",
    )
    url_token = fields.Char(
        string='Access token',
        required=True,
        help="Bearer token that authenticates this Odoo instance with the legacy cloud's REST API. Generate one from your account on the source cloud (My account -> API Keys) and paste it here.",
    )
    users_count = fields.Integer(
        default=0,
        help="Number of users discovered in the source cloud after Test Connection - informational, used to estimate import volume.",
    )
    company_dict = fields.Char(
        help="Internal mapping JSON (source-cloud company ID -> local res.company ID) cached after Test Connection. Not user-editable.",
    )
    ag_dict = fields.Char(
        help="Internal mapping JSON (source-cloud access-group ID -> local hr.rfid.access.group ID) cached after Test Connection. Not user-editable.",
    )

    connection_checked = fields.Boolean(
        default=False,
        help="True after Test Connection succeeded and the mapping dictionaries are populated. Gates the Import button.",
    )
    default_import_as = fields.Selection(
        [('contact', 'Contacts'), ('employee', 'Employees')],
        default='employee',
        help="How users from the source cloud become Odoo records - Employees: imported into hr.employee (full HR profile); Contacts: imported into res.partner (lighter, suitable for visitors).",
    )

    import_hardware = fields.Boolean(
        default=True,
        help="Include webstacks, controllers, doors and readers in the import.",
    )
    import_access_groups = fields.Boolean(
        default=True,
        help="Include access groups and their door bindings in the import.",
    )
    import_users = fields.Boolean(
        default=True,
        help="Include users (employees or contacts depending on Default Import As) and their card assignments.",
    )
    import_events = fields.Boolean(
        default=True,
        help="Include the historical access-event log. May be large - disable for a faster first import and re-run separately later.",
    )

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
            self.company_dict = [('-1', 'Old Cloud Customer')]
            self.connection_checked = True
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

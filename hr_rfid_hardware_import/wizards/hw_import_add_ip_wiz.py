from odoo import fields, models
from odoo.exceptions import UserError


class HwImportAddIpWiz(models.TransientModel):
    _name = 'hr.rfid.hw.import.add.ip.wiz'
    _description = 'Add a module by address'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade',
                             help="The survey the module is added to.")
    ip = fields.Char(required=True, help="Address of the module, e.g. 10.20.30.40.")
    port = fields.Integer(default=80, required=True, help="HTTP port; 80 unless the router forwards another.")
    module_username = fields.Selection([('admin', 'admin'), ('sdk', 'sdk')], default='sdk',
                                       help="Account on the module, only if it requires a password for reads.")
    module_password = fields.Char(help="Password for that account, if the module requires one.")

    def action_add(self):
        self.ensure_one()
        ip = (self.ip or '').strip()
        if not ip:
            raise UserError(self.env._("Enter the address of the module."))
        twin = self.run_id.module_ids.filtered(lambda m: m.ip == ip and (m.port or 80) == (self.port or 80))
        if twin:
            raise UserError(self.env._(
                "The module at %(ip)s is already in the survey; use Check again on its row instead.", ip=ip))
        module = self.env['hr.rfid.hw.import.module'].create({
            'run_id': self.run_id.id, 'source': 'manual', 'ip': ip, 'port': self.port or 80,
            'module_username': self.module_username, 'module_password': self.module_password or False,
        })
        self.run_id._probe_module(module)
        if module.status == 'unreachable':
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'type': 'warning', 'title': self.env._('Module not reachable'),
                           'message': self.env._('The module at %(ip)s did not answer. It stays in the list; '
                                                 'check the address and press Check again.', ip=ip),
                           'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}},
            }
        return {'type': 'ir.actions.act_window_close'}

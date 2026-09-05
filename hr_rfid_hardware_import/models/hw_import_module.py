from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HwImportModule(models.Model):
    _name = 'hr.rfid.hw.import.module'
    _description = 'Surveyed Module'
    _order = 'ip'

    run_id = fields.Many2one(
        'hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
        help="The survey that found this module.")
    source = fields.Selection([
        ('broadcast', 'Found on the network'),
        ('manual', 'Added by address'),
    ], required=True, default='broadcast',
        help="How the module got into the survey: answered the network search, "
             "or was typed in by address (a module behind a router).")
    ip = fields.Char(string="Address", required=True, help="Address the module is reached at, e.g. 192.168.1.50.")
    port = fields.Integer(string="Port", default=80, required=True,
                          help="HTTP port of the module's local interface; 80 unless forwarded.")
    hostname = fields.Char(string="Name", help="Name the module reports for itself.")
    mac = fields.Char(string="MAC address", help="Hardware address the module reports.")
    serial = fields.Char(string="Serial number", index=True, help="Serial number of the module; identifies it in this system.")
    hw_version = fields.Char(string="Hardware version", help="Module generation as it reports it (10.3, 50.1, 100.1).")
    fw_version = fields.Char(string="Firmware", help="Firmware version the module reports.")
    bridge_port = fields.Integer(string="Bridge port", help="Port of the module's raw bridge, reported at discovery; not used.")
    dev_found = fields.Integer(string="Controllers seen", help="How many controllers the module currently sees on its bus.")
    server_url = fields.Char(string="Reports to today",
        help="Which server the module reports to today. Shown only so you know who "
             "owns it; the survey never changes it.")
    status = fields.Selection([
        ('new', 'New'),
        ('known', 'Already in this system'),
        ('unreachable', 'Not reachable'),
    ], default='new', required=True, index=True,
        help="New: not registered here yet. Already in this system: a module with "
             "this serial exists here. Not reachable: it did not answer.")
    existing_webstack_id = fields.Many2one(
        'hr.rfid.webstack', string="Already registered as", ondelete='set null',
        help="The module record that already exists here with the same serial.")
    include = fields.Boolean(
        default=True,
        help="Read this module's controllers and include it in the import. "
             "Modules already in this system are left out unless you tick them.")
    module_username = fields.Selection([
        ('admin', 'admin'), ('sdk', 'sdk')], default='sdk',
        help="Account on the module, only needed when it requires a password for reads.")
    module_password = fields.Char(
        groups='base.group_system',
        help="Password for that account. The survey clears it when it ends, and after a day without "
             "activity; a module you import carries it on its own record, as any module added by hand.")
    config_json = fields.Text(string="Configuration read", help="The module configuration as read, with keys and passwords removed.")
    read_state = fields.Selection([
        ('pending', 'Not read yet'),
        ('reading', 'Reading'),
        ('done', 'Read'),
        ('failed', 'Failed'),
    ], default='pending', required=True,
        help="How far the reading of this module's controllers has got.")
    read_error = fields.Text(string="Reading problem", help="Why reading this module failed, if it did.")
    ctrl_ids = fields.One2many('hr.rfid.hw.import.ctrl', 'module_id', string='Controllers',
                               help="The controllers found on this module.")
    ctrl_count = fields.Integer(
        string="Number of controllers", compute="_compute_counts",
        help="Controllers the module sees on its bus. Fewer than the site has means a controller is "
             "off or unplugged; check the module's list after Check again.")
    webstack_id = fields.Many2one(
        'hr.rfid.webstack', string="Imported as", ondelete='set null',
        help="The module record created or reused by the import.")
    pointed_at = fields.Datetime(string="Pointed here on", help="When the module was told to report to this server.")
    pointed_by_id = fields.Many2one("res.users", string="Pointed here by", ondelete="set null",
                                    help="Who told the module to report to this server.")

    _ip_port_uniq = models.Constraint(
        'UNIQUE (run_id, ip, port)',
        'This address is already in the survey.')

    @api.constrains('serial', 'run_id')
    def _check_serial_unique_in_run(self):
        for module in self.filtered('serial'):
            twin = self.search([('run_id', '=', module.run_id.id), ('serial', '=', module.serial),
                                ('id', '!=', module.id)], limit=1)
            if twin:
                raise ValidationError(self.env._(
                    "Module %(serial)s is already in the survey at %(ip)s.",
                    serial=module.serial, ip=twin.ip))

    @api.depends('ctrl_ids')
    def _compute_counts(self):
        for module in self:
            module.ctrl_count = len(module.ctrl_ids)

    def _display_address(self):
        self.ensure_one()
        return self.ip if self.port in (80, 0, False) else '%s:%s' % (self.ip, self.port)

    def _auth(self):
        self.ensure_one()
        if self.sudo().module_password:
            return (self.module_username or 'sdk', self.sudo().module_password)
        return None

    def action_probe(self):
        """Ask the module again who it is and what it sees (synchronous, quick)."""
        for module in self:
            module.run_id._probe_module(module)
        return True

    def action_point_to_server(self):
        """The only write to a device this module ever makes - on request.

        Reuses the standard module setup of the access control module, so the
        device is configured exactly as if it had been added there.
        """
        self.ensure_one()
        if not self.webstack_id:
            raise UserError(self.env._(
                "Import the module first; then it can be pointed to this server."))
        if self.sudo().module_password and not self.webstack_id.module_password:
            self.webstack_id.sudo().write({
                'module_username': self.module_username,
                'module_password': self.sudo().module_password,
            })
        self.webstack_id.action_set_webstack_settings()
        self.write({'pointed_at': fields.Datetime.now(), 'pointed_by_id': self.env.user.id})
        self.run_id.message_post(body=self.env._(
            "Module %(name)s at %(ip)s was told to report to this server.",
            name=self.webstack_id.name, ip=self._display_address()))
        return True

    def action_enable_module(self):
        """Switch the imported module on in this system (a database change only)."""
        self.ensure_one()
        if not self.webstack_id:
            raise UserError(self.env._("Import the module first; then it can be enabled."))
        self.webstack_id.sudo().write({'active': True})
        self.run_id.message_post(body=self.env._(
            "Module %(name)s is now enabled in this system.", name=self.webstack_id.name))
        return True

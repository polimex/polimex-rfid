from odoo import fields, models, api


class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _inherit = ['hr.rfid.event.user']
    _description = "RFID User Event"

    site_id = fields.Many2one(
        'hr.rfid.site',
        string='Site',
        help='Event happened on this site',
        compute='_compute_site_id',
        store=True,
    )

    @api.depends('door_id', 'command_id', 'command_id.controller_id', 'command_id.webstack_id')
    def _compute_site_id(self):
        for record in self:
            record.site_id = record.door_id.site_id or record.command_id.controller_id.site_id or record.command_id.webstack_id.site_id

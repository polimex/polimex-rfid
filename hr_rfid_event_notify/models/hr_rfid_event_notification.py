from odoo import fields, models, api
from odoo.addons.hr_rfid.models.hr_rfid_event_user import action_selection


class ModelName(models.Model):
    _name = 'hr.rfid.event.notification'
    _description = 'Manage user notifications'

    ction = fields.Selection(
        selection=action_selection,
        string='Action',
        help='What happened to trigger the event',
        required=True,
    )

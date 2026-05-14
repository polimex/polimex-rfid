from odoo import models, fields, api

class HrRfidCard(models.Model):
    _name = 'hr.rfid.card'
    _inherit = 'hr.rfid.card'

    # New One2many field to store camera relations for this card
    camera_rel_ids = fields.One2many(
        'cctv.camera.rfid.rel',
        'card_id',
        string='Camera Relations',
        help="List of cameras in which this card is included"
    )
    # Computed field that counts the number of camera relations
    camera_count = fields.Integer(
        string='Camera Count',
        compute='_compute_camera_count',
        store=True,
        help="Number of ANPR cameras this card (license plate) is registered with. Drives the Cameras smart button on the card form.",
    )

    @api.depends('camera_rel_ids')
    def _compute_camera_count(self):
        for card in self:
            card.camera_count = len(card.camera_rel_ids)

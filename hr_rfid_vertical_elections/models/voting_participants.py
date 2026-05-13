from odoo import fields, models, api


class VotingParticipants(models.Model):
    _name = 'voting.participants'
    _description = 'Voting Participants'
    _inherit = ['mail.thread']


    name = fields.Char(
        string='Name of the voting Group',
        required=True,
        help="Label for this participants list (e.g. 'Board of Directors', 'Shareholders Class A'). Reused across multiple sessions.",
    )
    description = fields.Text(
        string='Description of the voting Group',
        help="Optional notes about who this group represents — useful as context when assigning the group to a session.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="Company that owns the participants list. Participants are isolated per company.",
    )
    participant_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Participants',
        required=True,
        help="Contacts allowed to vote. Each participant identifies themselves at the kiosk by tapping their RFID card on one of the configured terminals.",
    )
    terminal_ids = fields.Many2many(
        comodel_name='hr.rfid.door',
        string='Terminals',
        required=True,
        help="RFID readers participants will tap to identify themselves before casting a ballot. Multiple terminals let voters spread across separate queues.",
    )


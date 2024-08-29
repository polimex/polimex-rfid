from odoo import fields, models, api


class VotingParticipants(models.Model):
    _name = 'voting.participants'
    _description = 'Voting Participants'
    _inherit = ['mail.thread']


    name = fields.Char(
        string='Name of the voting Group',
        required=True,
    )
    description = fields.Text(
        string='Description of the voting Group',
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    participant_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Participants',
        required=True,
    )
    terminal_ids = fields.Many2many(
        comodel_name='hr.rfid.door',
        string='Terminals',
        required=True,
    )


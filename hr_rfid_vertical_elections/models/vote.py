from odoo import fields, models, api


class Vote(models.Model):
    _name = 'voting.vote'
    _description = 'Voting Vote'
    _rec_name = 'voting_item_id'

    voting_item_id = fields.Many2one(
        string='Voting for',
        comodel_name='voting.item',
        required=True
    )
    voting_session_id = fields.Many2one(
        comodel_name='voting.session',
        string='Voting Session',
        domain="[('state', '=', 'open')]",
        required=True
    )
    voter_id = fields.Many2one(
        comodel_name='res.partner',
        string='Voter',
        required=True
    )
    vote = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('abstain', 'Abstain'),
    ], required=True)
    vote_event_id = fields.Many2one(
        comodel_name='hr.rfid.event.user',
        domain="[('event_action', '=', '1'),]",
        string='Vote Event',
        # required=True,
    )
    vote_time = fields.Datetime(
        string='Vote Time',
        related='vote_event_id.event_time',
    )

    _sql_constraints = [
        ("uniq_vote", "unique(voting_session_id, voter_id)", "Vote must be unique"),
    ]

    def create(self, vals_list):
        vote = super(Vote, self).create(vals_list)
        vote.voting_session_id._compute_votes()
        return vote

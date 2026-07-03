from odoo import fields, models, api


class Vote(models.Model):
    _name = 'voting.vote'
    _description = 'Voting Vote'
    _rec_name = 'voting_item_id'

    voting_item_id = fields.Many2one(
        string='Voting for',
        comodel_name='voting.item',
        required=True,
        help="The question or motion this ballot answers.",
    )
    voting_session_id = fields.Many2one(
        comodel_name='voting.session',
        string='Voting Session',
        domain="[('state', '=', 'open')]",
        required=True,
        ondelete='cascade',
        help="Session in which the ballot was cast. New ballots can only be created against an Open session; if the session is deleted, its ballots cascade-delete with it.",
    )
    voter_id = fields.Many2one(
        comodel_name='res.partner',
        string='Voter',
        required=True,
        help="Participant who cast this ballot. Uniqueness is enforced - one ballot per voter per session.",
    )
    vote = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('abstain', 'Abstain'),
    ], required=True,
        help="Voter's answer.",
    )
    vote_event_id = fields.Many2one(
        comodel_name='hr.rfid.event.user',
        domain="[('event_action', '=', '1'),]",
        string='Vote Event',
        # required=True,
        help="The RFID Granted event recorded when the voter tapped their card on the terminal. Anchors the ballot to a physical action for audit purposes.",
    )
    vote_time = fields.Datetime(
        string='Vote Time',
        related='vote_event_id.event_time',
        help="Exact moment the voter tapped their card (read from the linked RFID event).",
    )

    _sql_constraints = [
        ("uniq_vote", "unique(voting_session_id, voter_id)", "Vote must be unique"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        vote = super().create(vals_list)
        vote.voting_session_id._compute_votes()
        return vote

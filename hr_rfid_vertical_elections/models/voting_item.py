from odoo import fields, models, api


class VotingItem(models.Model):
    _name = 'voting.item'
    _description = 'Voting Item'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(
        string='Name of the voting Item',
        required=True,
    )
    short_description = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    document = fields.Html(
        string='Document',
    )
    voting_session_id = fields.One2many(
        comodel_name='voting.session',
        inverse_name='item_ids',
        string='Voting Session',
        readonly=True,
    )
    vote_ids = fields.One2many(
        comodel_name='voting.vote',
        inverse_name='voting_item_id',
        string='Votes',
        readonly=True,
    )

from odoo import fields, models, api


class VotingItem(models.Model):
    _name = 'voting.item'
    _description = 'Voting Item'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(
        string='Name of the voting Item',
        required=True,
        help="Title of the question or motion (e.g. 'Approve 2026 budget'). Shown on the kiosk and on the audit report.",
    )
    short_description = fields.Text(
        help="Short summary of the question shown beside the title on the kiosk. Keep it under two sentences — the full motion goes into the Document field.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="Company that owns the voting item. Items are isolated per company.",
    )
    document = fields.Html(
        string='Document',
        help="Full text of the motion shown on the kiosk when the voter taps Read more. Use it for the legal wording, attached PDFs, or background information.",
    )
    voting_session_id = fields.One2many(
        comodel_name='voting.session',
        inverse_name='item_ids',
        string='Voting Session',
        readonly=True,
        help="Sessions that include this item. Read-only — managed from the session's Items list.",
    )
    vote_ids = fields.One2many(
        comodel_name='voting.vote',
        inverse_name='voting_item_id',
        string='Votes',
        readonly=True,
        help="Ballots cast for this item across all sessions. Useful for historical analysis of how the same motion fared over time.",
    )

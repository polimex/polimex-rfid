from email.policy import default

from wheel.metadata import requires_to_requires_dist

from odoo import fields, models, api
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class VotingSession(models.Model):
    _name = 'voting.session'
    _description = 'Voting Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name of the voting Session',
        required=True,
    )
    description = fields.Text(
        help='Description of the voting Session',
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    planned_date = fields.Date(
        string='Planned Vote Date',
        required=True,
        default=fields.Date.today,
        copy=False,
        tracking=True,
    )
    start_datetime = fields.Datetime(
        copy=False,
        tracking=True,
    )
    end_datetime = fields.Datetime(
        copy=False,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('revoted', 're-Voted'),
    ], default='draft', required=True, copy=False, tracking=True,)
    new_session_id = fields.Many2one(
        comodel_name='voting.session',
        string='New Session',
        readonly=True,
        copy=False,
    )
    old_session_id = fields.Many2one(
        comodel_name='voting.session',
        string='Old Session',
        readonly=True,
        copy=False,
    )
    participant_group_id = fields.Many2one(
        comodel_name='voting.participants',
        string='Participant Group',
        required=True,
    )
    item_ids = fields.Many2many(
        comodel_name='voting.item',
        string='Voting Items',
        required=True,
    )
    display_id = fields.Many2one(
        comodel_name='voting.display',
        string='Display',
        required=True,
    )
    voting_time = fields.Integer(
        string='Voting Time',
        help='Time in seconds for voting',
        default=30,
    )
    vote_results_time = fields.Integer(
        string='Vote Results Time',
        help='Time in seconds for showing the vote results',
        default=60,
    )

    vote_ids = fields.One2many(
        comodel_name='voting.vote',
        inverse_name='voting_session_id',
        string='Votes',
    )
    vote_yes = fields.Integer(
        string='Yes',
        compute='_compute_votes',
    )
    vote_no = fields.Integer(
        string='No',
        compute='_compute_votes',
    )
    vote_abstain = fields.Integer(
        string='Abstain',
        compute='_compute_votes',
    )
    vote_total = fields.Integer(
        string='All Votes',
        compute='_compute_votes',
    )
    final_vote = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('no_vote', 'No Vote'),
    ], default='no_vote', copy=False, compute='_compute_votes')

    def action_vote_result_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        lang = self.env.context.get('lang')
        mail_template = self.env.ref('hr_rfid_vertical_elections.mail_template_send_vote_result', raise_if_not_found=True)
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.constrains('state', 'display_id')
    def _check_display_state(self):
        for session in self:
            if session.state == 'open':
                open_sessions = self.search([
                    ('display_id', '=', session.display_id.id),
                    ('state', '=', 'open'),
                    ('id', '!=', session.id)
                ])
                if open_sessions:
                    raise ValidationError('Only one session can be open for a given display at a time.')

    @api.depends('vote_ids')
    def _compute_votes(self):
        for session in self:
            session.vote_yes = len(session.vote_ids.filtered(lambda vote: vote.vote == 'yes'))
            session.vote_no = len(session.vote_ids.filtered(lambda vote: vote.vote == 'no'))
            session.vote_abstain = len(session.vote_ids.filtered(lambda vote: vote.vote == 'abstain'))
            session.vote_total = len(session.vote_ids)
            if session.vote_total == 0:
                session.final_vote = 'no_vote'
            else:
                session.final_vote = 'yes' if session.vote_yes > session.vote_no else 'no'
            if session.state in ['open', 'closed']:
                session.display_id._notify_display_view("voting", session)

    def open_votes_action(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Votes',
            'res_model': 'voting.vote',
            'view_mode': 'tree,form',
            'domain': [('voting_session_id', '=', self.id)],
            'context': {'default_voting_session_id': self.id},
        }

    def button_open_voting_session(self):
        self.write({
            'state': 'open',
            'start_datetime': fields.Datetime.now()
        })

    def button_close_voting_session(self):
        self.write({
            'state': 'closed',
            'end_datetime': fields.Datetime.now()
        })

    def notify_voting_session_state(self):
        for session in self:
            session.display_id._notify_display_view("change_state", sessions=[session])

    def button_re_voting_session(self):
        revoute_id = self.copy(default={'state': 'draft', 'old_session_id': self.id})
        self.write({
            'state': 'revoted',
            'new_session_id': revoute_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': revoute_id.id,
            'target': 'current',
        }

    def write(self, vals):
        # Log vals in _logger.info
        if 'state' in vals and vals['state'] == 'draft':
            vals['start_datetime'] = False
            vals['end_datetime'] = False
        for session in self:
            if not session.vote_ids and vals.get('state') == 'closed':
                # TODO Need separation between sessions with votes and without votes
                vals['state'] = 'draft'
        result = super(VotingSession, self).write(vals)
        reload_fields = {'final_vote', 'vote_yes', 'vote_no', 'vote_total', 'vote_abstain'}
        if 'state' in vals:
            for session in self:
                session.notify_voting_session_state()
        elif not reload_fields.intersection(vals):
            for session in self:
                session.display_id._notify_display_view("reload")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super().create(vals_list)
        for session in sessions:
            session.display_id._notify_display_view("reload")
        return sessions
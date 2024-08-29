from odoo import fields, models, api, _
from uuid import uuid4
from odoo.tools.translate import html_translate

import logging
_logger = logging.getLogger(__name__)

class VotingDisplay(models.Model):
    _name = 'voting.display'
    _inherit = ["mail.thread"]
    _description = 'Voting Display'


    name = fields.Char(
        string='Name of the voting Display',
        required=True,
    )
    description = fields.Html(string="Announcements", translate=html_translate)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    voting_session_ids = fields.One2many(
        comodel_name='voting.session',
        inverse_name='display_id',
        string='Voting Display',
        readonly=True,
    )
    short_code = fields.Char("Short Code", default=lambda self: str(uuid4())[:8], copy=False, required=True, tracking=1)
    # Technical/Statistics
    access_token = fields.Char("Access Token", default=lambda self: str(uuid4()), copy=False, readonly=True, required=True)
    display_url = fields.Char("Voting Display URL", compute="_compute_display_url")
    # Frontend design fields
    no_voting_background_color = fields.Char("No Voting Background Color", default="#83c5be")
    voting_background_color = fields.Char("Voting Background Color", default="#dd2d4a")
    display_background_image = fields.Image("Background Image")

    voting_sessions_count = fields.Integer("Voting Sessions Count", compute="_compute_voting_sessions_count")

    _sql_constraints = [
        ("uniq_access_token", "unique(access_token)", "The access token must be unique"),
        ("uniq_short_code", "unique(short_code)", "The short code must be unique."),
    ]

    def regenerate_display_key(self):
        self.ensure_one()
        self.write({
            'short_code': str(uuid4())[:8],
            'access_token': str(uuid4())
        })

    @api.depends("voting_session_ids")
    def _compute_voting_sessions_count(self):
        voting_sessions_count_by_display = dict(self.env["voting.session"]._read_group(
            [("display_id", "in", self.ids)],
            ["display_id"],
            ["__count"]
        ))
        for display in self:
            display.voting_sessions_count = voting_sessions_count_by_display.get(display, 0)
            display._notify_display_view("reload")


    @api.depends("short_code")
    def _compute_display_url(self):
        for display in self:
            display.display_url = f"{display.get_base_url()}/voting_display/{display.short_code}/voting"
        # for room in self:
        #     room.room_booking_url = f"{room.get_base_url()}/room/{room.short_code}/book"


    def action_open_display_view(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.display_url,
            "target": "new",
        }
    def action_view_sessions(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "voting.session",
            "name": _("Sessions for %s" % self.name),
            "domain": [("display_id", "in", self.ids)],
            "context": {"default_display_id": self.id if len(self) == 1 else False},
            "view_mode": "kanban,tree,form",
        }

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    def _notify_display_view(self, method, sessions=False):
        """ Notify.
        """
        self.ensure_one()
        _logger.info(f"Notify display view: {method}")
        msg_prefix = 'display'
        if method == "reload":
            self.env["bus.bus"]._sendone(f"{msg_prefix}#{self.access_token}", "reload", self.display_url)
        elif method in ["change_state"]:
            # Retrieve all fields from the model dynamically
            # fields = self.env['voting.session']._fields
            self.env["bus.bus"]._sendone(
                f"{msg_prefix}#{self.access_token}",
                f"session/{method}",
                [{
                    # field: getattr(session, field)
                    # for field in fields
                    "id": session.id,
                    "name": session.name,
                    "planned_date": session.planned_date,
                    "start_datetime": session.start_datetime,
                    "end_datetime": session.end_datetime,
                    "state": session.state,
                    "vote_yes": session.vote_yes,
                    "vote_no": session.vote_no,
                    "vote_abstain": session.vote_abstain,
                    "vote_total": session.vote_total,
                    "final_vote": session.final_vote,
                    "voting_time": session.voting_time,
                    "vote_results_time": session.vote_results_time,
                } for session in (sessions or [])]
            )
        elif method in ["voting"]:
            self.env["bus.bus"]._sendone(
                f"{msg_prefix}#{self.access_token}",
                f"session/{method}",
                [{
                    "id": session.id,
                    "vote_yes": session.vote_yes,
                    "vote_no": session.vote_no,
                    "vote_abstain": session.vote_abstain,
                    "vote_total": session.vote_total,
                    "final_vote": session.final_vote,
                } for session in (sessions or [])]
            )
        else:
            raise NotImplementedError(f"Method '{method}' is not implemented for '_notify_display_view'")
from odoo import fields, models, api

import logging
_logger = logging.getLogger(__name__)

class HrRfidUserEvent(models.Model):
    _inherit = 'hr.rfid.event.user'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for res in self.filtered(lambda res: res.event_action == '1'):
            _logger.info('Voting event detected')
            open_vote_session_ids = self.env['voting.session'].search([('state', '=', 'open')])
            _logger.info('Open voting sessions: %s', open_vote_session_ids)
            open_vote_session_for_this_door = open_vote_session_ids.filtered(lambda session: res.door_id in session.participant_group_id.terminal_ids)
            _logger.info('Open voting sessions for this door: %s', open_vote_session_for_this_door)
            if open_vote_session_for_this_door and res.contact_id in open_vote_session_for_this_door.participant_group_id.participant_ids:
                workcode_id = res.workcode_id
                _logger.info('Workcode: %s', workcode_id)
                if res.event_time >= open_vote_session_for_this_door[0].start_datetime and workcode_id.user_action in ['yes', 'no', 'abstain']:
                    vote = self.env['voting.vote'].create({
                    'voting_item_id': open_vote_session_for_this_door[0].item_ids.ids[0],
                    'voting_session_id': open_vote_session_for_this_door[0].id,
                    'voter_id': res.contact_id.id,
                    'vote': workcode_id.user_action,
                    'vote_event_id': res.id,
                })
                    _logger.info('Vote created: %s', vote)
        return res

    def re_vote_event(self):
        self.ensure_one()
        open_vote_session_ids = self.env['voting.session'].search([('state', '=', 'open')])
        open_vote_session_for_this_door = open_vote_session_ids.filtered(lambda session: self.door_id in session.participant_group_id.terminal_ids)
        if open_vote_session_for_this_door and self.contact_id in open_vote_session_for_this_door.participant_group_id.participant_ids:
            workcode_id = self.workcode_id
            if workcode_id.user_action in ['yes', 'no', 'abstain']:
                vote = self.env['voting.vote'].create({
                    'voting_item_id': open_vote_session_for_this_door[0].item_ids.ids[0],
                    'voting_session_id': open_vote_session_for_this_door[0].id,
                    'voter_id': self.contact_id.id,
                    'vote': workcode_id.user_action,
                    'vote_event_id': self.id,
                })
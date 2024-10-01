from odoo import fields, models, api


class HrRfidUserEvent(models.Model):
    _inherit = 'hr.rfid.event.user'


    def create(self, vals_list):
        res = super(HrRfidUserEvent, self).create(vals_list)
        for res in self.filtered(lambda res: res.event_action == '1'):
            open_vote_session_ids = self.env['voting.session'].search([('state', '=', 'open')])
            open_vote_session_for_this_door = open_vote_session_ids.filtered(lambda session: res.door_id in session.participant_group_id.terminal_ids)
            if open_vote_session_for_this_door and res.contact_id in open_vote_session_for_this_door.participant_group_id.participant_ids:
                workcode_id = res.workcode_id
                if res.event_time >= open_vote_session_for_this_door[0].start_date and workcode_id.user_action in ['yes', 'no', 'abstain']:
                    vote = self.env['voting.vote'].create({
                    'voting_item_id': open_vote_session_for_this_door[0].item_ids.ids[0],
                    'voting_session_id': open_vote_session_for_this_door[0].id,
                    'voter_id': res.contact_id.id,
                    'vote': workcode_id.user_action,
                    'vote_event_id': res.id,
                })
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
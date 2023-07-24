from datetime import timedelta

from odoo import fields, models, api, exceptions, _


class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _inherit = 'hr.rfid.event.system'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(HrRfidSystemEvent, self).create(vals_list)
        if any([e.event_action != '34' for e in res]):
            res.refresh_views()
        for e in res:
            # if e.event_action in ['19', '20', '25', '26', '30']:
            if e.event_action in ['19', '20']:
                key_val_dict = dict(e._fields['event_action'].selection)
                title = key_val_dict[e.event_action]
                message = e.error_description
                if e.event_action == '20':
                    message = _('Siren %s', e.siren and 'On' or 'Off')
                e.controller_id.webstack_id.message_follower_ids.notify_browser_followers(
                    title=title,
                    message=message,
                )
                e.controller_id.webstack_id.message_follower_ids.notify_web_followers(
                    title=title,
                    message=message,
                    sticky=True,
                    m_type='danger')
        return res

    def write(self, vals):
        res = super(HrRfidSystemEvent, self).write(vals)
        self.refresh_views()
        return res


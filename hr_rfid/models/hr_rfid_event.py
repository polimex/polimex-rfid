from odoo import fields, models, api


class HRRFIDEvent(models.AbstractModel):
    _name = 'hr.rfid.event'
    _description = 'Helper for RFID Events'

    def get_event_action_text(self):
        self.ensure_one()
        selection_dict = dict(self.fields_get(allfields=['event_action'])['event_action']['selection'])
        state_text = selection_dict.get(self.event_action)
        return state_text

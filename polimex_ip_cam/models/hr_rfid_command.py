from odoo import fields, models, api
from odoo.addons.hr_rfid.models.hr_rfid_door import HrRfidDoor


class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _inherit = 'hr.rfid.command'

    @api.model
    def add_card(self, door_id, ts_id, pin_code, card_id, alarm_right):
        door = door_id and isinstance(door_id, HrRfidDoor) and door_id or self.env['hr.rfid.door'].browse(door_id)
        door = self.env['hr.rfid.door'].browse(door_id)
        time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        if door.camera_id and card:
            door.camera_id.add_card_id_to_list(card)
        else:
            super().add_card(door_id, ts_id, pin_code, card_id, alarm_right)


    @api.model
    def remove_card(self, door_id, pin_code, card_number=None, card_id=None):
        door = door_id and isinstance(door_id, HrRfidDoor) and door_id or self.env['hr.rfid.door'].browse(door_id)
        door = self.env['hr.rfid.door'].browse(door_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        if door.camera_id:
            door.camera_id.remove_card_id_from_list(card)
        else:
            super().remove_card(door_id, pin_code, card_number, card_id)
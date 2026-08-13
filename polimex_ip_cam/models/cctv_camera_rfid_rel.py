from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Mapping from the Odoo list_category to the numeric listType value the camera
# API expects. Matches the Hikvision ISAPI standard: 0 = whitelist (allow),
# 1 = blacklist (deny). Only these two buckets are supported by the hardware.
LIST_TYPE_MAP = {
    'whitelist': '0',
    'blacklist': '1',
}


class CctvCameraRfidRel(models.Model):
    _name = 'cctv.camera.rfid.rel'
    _description = 'CCTV Camera - RFID Card Relation'

    camera_id = fields.Many2one(
        comodel_name='cctv.camera', string='Camera', required=True, ondelete='cascade', index=True,
        help="Camera to which this card relation belongs")
    card_id = fields.Many2one(
        comodel_name='hr.rfid.card', string='RFID Card', required=True, ondelete='cascade',
        domain=lambda self: [('card_type', '=', self.env.ref('hr_rfid.hr_rfid_card_type_8').id)],
        help="Linked license plate or other vehicle identifier")
    list_category = fields.Selection([
        ('whitelist', 'Whitelist'),
        ('blacklist', 'Blacklist'),
    ], string='List Category', required=True, default='whitelist',
       help="The type of list this relation represents")

    def _hv_get_request_data(self):
        # This method is used to generate the request data for the Hikvision camera.
        # It should be overridden in subclasses if needed.
        self.ensure_one()
        rec = self
        if rec.camera_id and rec.camera_id.brand == 'hikvision' and rec.card_id.card_type == self.env.ref(
                'hr_rfid.hr_rfid_card_type_8'):
            plate_number = rec.card_id.number or ''
            if plate_number:
                # listType the camera expects: '0' whitelist, '1' blacklist.
                list_type = LIST_TYPE_MAP.get(rec.list_category, '0')
                # Използваме новите опционални полета:
                other_card_ids = rec.card_id.get_owner().hr_rfid_card_ids.filtered(
                    lambda c: c.card_type != self.env.ref('hr_rfid.hr_rfid_card_type_8'))
                card_no = other_card_ids[0].number if other_card_ids else ''
                # Полетата validity_start и validity_end са винаги в UTC в Odoo.
                validity_start = rec.card_id.activate_on and (
                        rec.card_id.activate_on.isoformat() + "Z") or "0000-00-00T00:00:00Z"
                validity_end = rec.card_id.deactivate_on and (
                            rec.card_id.deactivate_on.isoformat() + "Z") or "0000-00-00T00:00:00Z"
                # Изграждаме request_data като редове с формат param=value
                lines = [
                    "plateNum=" + plate_number,
                    "listType=" + str(list_type),
                ]
                if card_no:
                    lines.append("cardNo=" + card_no)
                if rec.card_id.activate_on and rec.card_id.deactivate_on:
                    lines.append("startTime=" + rec.card_id.activate_on.isoformat() + "Z")
                    lines.append("endTime=" + rec.card_id.deactivate_on.isoformat() + "Z")
                return "\n".join(lines)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('no_hardware_commands'):
            # Migration writes the picture as it already is on the camera - it
            # must not talk to the device. Same convention as hr_rfid
            # (hr_rfid_door.py:840): without it, moving a few hundred plates
            # fires a few hundred HTTP requests at cameras that are guarding a
            # live site.
            return records
        # For each created relation, create an "add_plate" command
        cmd_env = self.env['cctv.camera.command'].sudo()
        for rec in records:
            request_data = rec._hv_get_request_data()
            if request_data:
                try:
                    cmd_env.create([{
                        'camera_id': rec.camera_id.id,
                        'command_type': 'add_plate',
                        'request_data': request_data,
                    }])
                except Exception as e:
                    _logger.error("Error creating add_plate command for relation ID %s: %s", rec.id, e)
        return records

    def unlink(self):
        if self.env.context.get('no_hardware_commands'):
            return super().unlink()
        # Before deletion, for each relation, create a "remove_plate" command if applicable.
        cmd_env = self.env['cctv.camera.command'].sudo()
        for rec in self:
            if rec.camera_id and rec.camera_id.brand == 'hikvision' and rec.card_id.card_type==self.env.ref('hr_rfid.hr_rfid_card_type_8'):
                plate_number = rec.card_id.number or ''
                if plate_number:
                    request_data = "plateNum={}".format(plate_number)
                    try:
                        cmd_env.create([{
                            'camera_id': rec.camera_id.id,
                            'command_type': 'remove_plate',
                            'request_data': request_data,
                        }])
                    except Exception as e:
                        _logger.error("Error creating remove_plate command for relation ID %s: %s", rec.id, e)
        return super().unlink()

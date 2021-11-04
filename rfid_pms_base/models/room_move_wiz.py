from odoo import fields, models, api


class RoomMoveWiz(models.TransientModel):
    _name = 'rfid_pms_base.room_move_wiz'
    _description = 'Move customers from one room to another'

    def _get_room_id(self):
        return self.env['rfid_pms_base.room'].browse(self._context.get("active_id", []))

    def _get_free_room_id(self):
        free_ids = self.env['rfid_pms_base.room'].search([
            ('reservation', '=', 'False')
        ]).filtered(lambda i: i.id != self._get_room_id().id).mapped('id')
        res = "[('id', 'in', {})]".format(free_ids)
        return res

    room_from_id = fields.Many2one(comodel_name='rfid_pms_base.room', default=_get_room_id)
    room_to_id = fields.Many2one(comodel_name='rfid_pms_base.room', domain=_get_free_room_id, required=True)

    def move_customers(self):
        self.room_from_id.all_contact_ids.access_group_id = self.room_to_id.access_group_id


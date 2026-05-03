from odoo import fields, models


class RoomMoveWiz(models.TransientModel):
    _name = 'rfid_pms_base.room_move_wiz'
    _description = 'Move customers from one room to another'

    def _get_room_id(self):
        return self.env['rfid_pms_base.room'].browse(self.env.context.get("active_id", []))

    def _get_free_room_domain(self):
        # 'reservation' is a non-stored computed field (Many2one), so we
        # must materialise the candidate set in Python rather than embed
        # it in the SQL domain — Odoo 19 rejects non-stored fields in
        # ORM domains.
        excluded_id = self._get_room_id().id
        free_room_ids = self.env['rfid_pms_base.room'].search([]).filtered(
            lambda r: not r.reservation and r.id != excluded_id
        ).ids
        return [('id', 'in', free_room_ids)]

    room_from_id = fields.Many2one(comodel_name='rfid_pms_base.room', default=_get_room_id)
    room_to_id = fields.Many2one(comodel_name='rfid_pms_base.room', domain=_get_free_room_domain, required=True)

    def move_customers(self):
        self.room_from_id.all_contact_ids.access_group_id = self.room_to_id.access_group_id


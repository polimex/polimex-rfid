from odoo import fields, models


class RoomMoveWiz(models.TransientModel):
    _name = 'rfid_pms_base.room_move_wiz'
    _description = 'Move customers from one room to another'

    def _get_room_id(self):
        return self.env['rfid_pms_base.room'].browse(self.env.context.get("active_id", []))

    def _get_free_room_domain(self):
        # `reservation` is a non-stored compute (Many2one) so it cannot live
        # inside an ORM domain. We approximate "free" as "AG has no contact
        # rel" — same condition `_compute_reservation` uses — via a batched
        # prefetch instead of per-room compute calls.
        excluded_id = self._get_room_id().id
        rooms = self.env['rfid_pms_base.room'].search([('id', '!=', excluded_id)])
        rooms.mapped('all_contact_ids')
        free_ids = [r.id for r in rooms if not r.all_contact_ids]
        return [('id', 'in', free_ids)]

    room_from_id = fields.Many2one(comodel_name='rfid_pms_base.room', default=_get_room_id)
    room_to_id = fields.Many2one(comodel_name='rfid_pms_base.room', domain=_get_free_room_domain, required=True)

    def move_customers(self):
        self.room_from_id.all_contact_ids.access_group_id = self.room_to_id.access_group_id


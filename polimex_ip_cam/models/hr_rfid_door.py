from odoo import fields, models, api, SUPERUSER_ID


class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _inherit = 'hr.rfid.door'

    camera_id = fields.Many2one(
        comodel_name="cctv.camera",
        string="Camera",
        related="reader_ids.camera_id",
        ondelete="cascade",
        store=True,
        index=True,
        help="ANPR camera bound to this door's reader (inherited via the reader). When set, card-to-door assignments are mirrored to the camera's whitelist automatically.",
    )

    @api.depends('webstack_id', 'camera_id')
    def compute_company_id(self):
        for door in self:
            if door.camera_id:
                door.company_id = door.camera_id.company_id.id
            else:
                door.company_id = door.webstack_id.company_id if door.webstack_id else False

class HrRfidCardDoorRel(models.Model):
    _name = 'hr.rfid.card.door.rel'
    _inherit = 'hr.rfid.card.door.rel'

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['hr.rfid.card.door.rel']

        for vals in vals_list:
            # Always create the rel. Earlier the create was skipped — and the
            # record silently dropped from the result — whenever vals had no
            # door_id, breaking callers that set the door link separately.
            if vals.get('door_id') and vals.get('card_id'):
                door = self.env['hr.rfid.door'].browse(vals['door_id'])
                if door.camera_id:
                    door.camera_id.add_card_id_to_list(vals['card_id'])
            records += super().create([vals])
        return records

    def write(self, vals):
        for rel in self.with_user(SUPERUSER_ID):
            old_door = rel.door_id
            old_card = rel.card_id
            old_ts_id = rel.time_schedule_id

            super().write(vals)

            new_door = rel.door_id
            new_card = rel.card_id
            new_ts_id = rel.time_schedule_id

            if old_door.camera_id and (old_door != new_door or old_card != new_card):
                old_door.camera_id.remove_card_id_from_list(old_card.id)
                new_door.camera_id.add_card_id_to_list(new_card)

    def unlink(self, create_cmd=True):
        if create_cmd:
            for rel in self:
                if rel.door_id.camera_id:
                    rel.door_id.camera_id.remove_card_id_from_list(rel.card_id.id)
        return super().unlink(create_cmd=create_cmd)
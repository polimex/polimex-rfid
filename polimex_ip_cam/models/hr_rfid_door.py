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

    @api.depends('webstack_id', 'webstack_id.company_id', 'camera_id', 'camera_id.company_id')
    def compute_company_id(self):
        for door in self:
            if door.camera_id:
                door.company_id = door.camera_id.company_id.id
            else:
                door.company_id = door.webstack_id.company_id if door.webstack_id else False

class HrRfidCardDoorRel(models.Model):
    _name = 'hr.rfid.card.door.rel'
    _inherit = 'hr.rfid.card.door.rel'

    def _mirrors_to_camera(self):
        """Whether card-to-door changes should reach the camera's plate list.

        A migration writes the picture the camera already holds, so it must not
        push it back - and, more importantly, the mirror CREATES
        cctv.camera.rfid.rel rows of its own. Those rows carry no source id, so
        they collide with the ones the migration brings across, and afterwards
        nobody can tell which link is the real one.
        """
        return not self.env.context.get('no_hardware_commands')

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['hr.rfid.card.door.rel']
        mirror = self._mirrors_to_camera()

        for vals in vals_list:
            # Always create the rel. Earlier the create was skipped - and the
            # record silently dropped from the result - whenever vals had no
            # door_id, breaking callers that set the door link separately.
            if mirror and vals.get('door_id') and vals.get('card_id'):
                door = self.env['hr.rfid.door'].browse(vals['door_id'])
                if door.camera_id:
                    door.camera_id.add_card_id_to_list(vals['card_id'])
            records += super().create([vals])
        return records

    def write(self, vals):
        mirror = self._mirrors_to_camera()
        res = True
        for rel in self.with_user(SUPERUSER_ID):
            old_door = rel.door_id
            old_card = rel.card_id

            # Bound to `rel`, not to `self`: a bare super().write() inside the
            # loop writes the WHOLE recordset on every pass, so from the second
            # record onwards old_door/old_card were already the new values and
            # the camera mirror ran against the wrong door. It also returned
            # None, while the ORM contract is a truthy value.
            res = super(HrRfidCardDoorRel, rel).write(vals)

            new_door = rel.door_id
            new_card = rel.card_id

            if mirror and old_door.camera_id and (
                    old_door != new_door or old_card != new_card):
                old_door.camera_id.remove_card_id_from_list(old_card.id)
                new_door.camera_id.add_card_id_to_list(new_card)
        return res

    def unlink(self, create_cmd=True):
        if create_cmd and self._mirrors_to_camera():
            for rel in self:
                if rel.door_id.camera_id:
                    rel.door_id.camera_id.remove_card_id_from_list(rel.card_id.id)
        return super().unlink(create_cmd=create_cmd)
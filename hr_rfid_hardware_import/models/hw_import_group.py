import hashlib
import json

from odoo import api, fields, models


class HwImportGroup(models.Model):
    _name = 'hr.rfid.hw.import.group'
    _description = 'Proposed Access Group'
    _order = 'sequence, id'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey that proposed this group.")
    sequence = fields.Integer(default=10, help="Order in the list.")
    name = fields.Char(size=32, required=True,
                       help="Name the access group will get. You can rename it before the import.")
    holder_key = fields.Char(string="Card set fingerprint", index=True,
                             help="Fingerprint of the set of cards that share these rights.")
    card_ids = fields.Many2many('hr.rfid.hw.import.card', 'hw_import_group_card_rel', 'group_id', 'card_id',
                                string='Cards', help="The cards that hold every right of this group.")
    card_count = fields.Integer(string="Number of cards", compute='_compute_counts', store=True, help="How many cards are in the group.")
    right_ids = fields.One2many('hr.rfid.hw.import.group.right', 'group_id', string='Rights',
                                help="The doors this group opens, with schedule and alarm right.")
    door_count = fields.Integer(string="Number of doors", compute='_compute_counts', store=True, help="How many doors the group opens.")
    include = fields.Boolean(default=True, help="Create this access group during the import.")
    merged_from_json = fields.Text(string="Merged from", help="Which proposed groups were merged into this one, if any.")
    access_group_id = fields.Many2one('hr.rfid.access.group', string="Imported as", ondelete='set null',
                                      help="The access group created by the import.")

    _holder_uniq = models.Constraint(
        'UNIQUE (run_id, holder_key)',
        'Two proposed groups cannot hold the same set of cards.')

    @api.depends('card_ids', 'right_ids')
    def _compute_counts(self):
        for group in self:
            group.card_count = len(group.card_ids)
            group.door_count = len(group.right_ids)

    @api.model
    def _holder_key_for(self, cards):
        """Fingerprint of a set of cards: the identity of a proposed group."""
        return hashlib.sha1(json.dumps(sorted(cards.mapped('number'))).encode()).hexdigest()


class HwImportGroupRight(models.Model):
    _name = 'hr.rfid.hw.import.group.right'
    _description = 'Proposed Access Group Right'
    _order = 'ctrl_id, door_number'

    group_id = fields.Many2one('hr.rfid.hw.import.group', required=True, ondelete='cascade', index=True,
                               help="The proposed group this right belongs to.")
    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey this right belongs to.")
    ctrl_id = fields.Many2one('hr.rfid.hw.import.ctrl', string="Controller", required=True, ondelete='cascade', index=True,
                              help="The controller the door is on.")
    door_number = fields.Integer(string="Door number", required=True, help="Door number on that controller.")
    ts_number = fields.Integer(string="Schedule slot", required=True, help="Time schedule slot the right uses (0 = always).")
    alarm = fields.Boolean(string="Alarm right", help="The right includes arming and disarming the door's alarm.")
    door_rec_id = fields.Many2one('hr.rfid.door', string="Door here", ondelete='set null',
                                  help="The door record the right was granted on, after the import.")
    door_label = fields.Char(string="Door", compute='_compute_door_label', help="Controller and door, in words.")

    _right_uniq = models.Constraint(
        'UNIQUE (run_id, ctrl_id, door_number, ts_number, alarm)',
        'Each right belongs to exactly one proposed group.')

    @api.depends('ctrl_id.name', 'door_number', 'ts_number', 'alarm')
    def _compute_door_label(self):
        for right in self:
            label = self.env._('%(ctrl)s door %(door)s', ctrl=right.ctrl_id.name, door=right.door_number)
            if right.ts_number:
                label += self.env._(' (schedule %(ts)s)', ts=right.ts_number)
            if right.alarm:
                label += self.env._(' + alarm')
            right.door_label = label


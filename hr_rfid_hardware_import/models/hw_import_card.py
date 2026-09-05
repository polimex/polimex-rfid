import json

from odoo import api, fields, models

ANOMALIES = [
    ('none', 'None'),
    ('bad_bcd', 'Number is not readable'),
    ('reader_ts_mismatch', 'Readers of one door have different schedules'),
    ('partial_reader', 'Only some readers of a door'),
    ('no_rights', 'Opens no door'),
    ('pin_mismatch', 'PIN differs between controllers'),
]


class HwImportCard(models.Model):
    _name = 'hr.rfid.hw.import.card'
    _description = 'Surveyed Card'
    _order = 'number'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey that found this card.")
    number = fields.Char(string="Number (as stored)", size=10, required=True, index=True,
                         help="The card number as the controllers hold it (ten digits).")
    number_display = fields.Char(string="Card number", help="The card number in the form this company writes card numbers.")
    pin = fields.Char(string="PIN", size=4, help="PIN code stored with the card, when the controllers hold one.")
    pin_mismatch = fields.Boolean(string="PIN codes differ", help="Controllers hold different PIN codes for this card.")
    record_ids = fields.One2many('hr.rfid.hw.import.card.record', 'card_id', string='Records',
                                 help="One line per controller that holds this card.")
    door_rights_json = fields.Text(string="Doors opened", help="The doors this card opens, with schedule and alarm right (derived).")
    rights_key = fields.Char(string="Rights fingerprint", index=True, help="Fingerprint of the card's rights, used to compare cards.")
    apb_bits_json = fields.Text(string="Anti-passback state", help="Anti-passback state bits per controller; recorded only, never imported.")
    anomaly = fields.Selection(ANOMALIES, default='none', required=True, index=True,
                               help="Something about this card's records that cannot be represented exactly.")
    person_id = fields.Many2one('hr.rfid.hw.import.person', ondelete='set null', index=True,
                                help="Who will own this card after the import.")
    group_ids = fields.Many2many('hr.rfid.hw.import.group', 'hw_import_group_card_rel', 'card_id', 'group_id',
                                 string='Access groups', help="The proposed access groups this card belongs to.")
    existing_card_id = fields.Many2one('hr.rfid.card', string="Existing card", ondelete='set null',
                                       help="A card with this number that already exists here.")
    card_rec_id = fields.Many2one('hr.rfid.card', string="Imported as", ondelete='set null',
                                  help="The card record created or reused by the import.")
    include = fields.Boolean(default=True, help="Include this card in the import.")
    door_count = fields.Integer(string="Number of doors", compute='_compute_door_count', help="How many doors this card opens.")

    _number_uniq = models.Constraint(
        'UNIQUE (run_id, number)',
        'A survey holds each card number once.')

    @api.depends('door_rights_json')
    def _compute_door_count(self):
        for card in self:
            # The analysis writes this field; a value that does not parse is a
            # defect to see, not a card with no doors.
            card.door_count = len(json.loads(card.door_rights_json or '[]'))


class HwImportCardRecord(models.Model):
    _name = 'hr.rfid.hw.import.card.record'
    _description = 'Surveyed Card Record'
    _order = 'ctrl_id, position'

    card_id = fields.Many2one('hr.rfid.hw.import.card', required=True, ondelete='cascade', index=True,
                              help="The card this record belongs to.")
    ctrl_id = fields.Many2one('hr.rfid.hw.import.ctrl', required=True, ondelete='cascade', index=True,
                              help="The controller this record was read from.")
    position = fields.Integer(string="Position in the table", help="Position of the record in the controller's card table.")
    raw_hex = fields.Char(string="Record (raw)", help="The raw record as read (evidence).")
    pin = fields.Char(string="PIN", size=4, help="PIN code in this record.")
    ts_r1 = fields.Integer(string="Schedule, reader 1", help="Time schedule slot for reader 1 (0 = always).")
    ts_r2 = fields.Integer(string="Schedule, reader 2", help="Time schedule slot for reader 2 (0 = always).")
    ts_r3 = fields.Integer(string="Schedule, reader 3", help="Time schedule slot for reader 3 (0 = always).")
    ts_r4 = fields.Integer(string="Schedule, reader 4", help="Time schedule slot for reader 4 (0 = always).")
    rights = fields.Integer(string="Readers accepting the card", help="Rights byte: which readers accept the card.")
    apb1 = fields.Boolean(string="Anti-passback state 1", help="Anti-passback state bit 1 as read (recorded only).")
    apb2 = fields.Boolean(string="Anti-passback state 2", help="Anti-passback state bit 2 as read (recorded only).")
    alarm_bits = fields.Integer(string="Alarm zones", help="Alarm zones this card may arm or disarm (bit per zone).")
    anomaly = fields.Char(string="Unusual", help="Something unusual about this record, if anything.")

    _ctrl_card_uniq = models.Constraint(
        'UNIQUE (ctrl_id, card_id)',
        'A controller holds each card once.')

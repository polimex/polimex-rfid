from odoo import fields, models


class HwImportName(models.Model):
    _name = 'hr.rfid.hw.import.name'
    _description = 'Names File Line'
    _order = 'row_number'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey the file was uploaded to.")
    row_number = fields.Integer(string="Line", help="Line number in the uploaded file.")
    name_raw = fields.Char(string="Name in the file", help="The name exactly as written in the file.")
    number_raw = fields.Char(string="Card number in the file", help="The card number exactly as written in the file.")
    number_norm = fields.Char(string="Card number (as stored)", help="The card number as the controllers would hold it.")
    card_id = fields.Many2one('hr.rfid.hw.import.card', string="Matched card", ondelete='set null', index=True,
                              help="The surveyed card this line matched.")
    person_id = fields.Many2one('hr.rfid.hw.import.person', string="Person", ondelete='set null', index=True,
                                help="The person this line was folded into.")
    status = fields.Selection([
        ('matched', 'Matched a card'),
        ('unmatched', 'No such card on any controller'),
        ('duplicate', 'Number repeated in the file'),
        ('invalid', 'Not a card number'),
    ], required=True, default='unmatched', index=True,
        help="What happened to this line. Only matched lines name a card.")
    note = fields.Char(string="Note", help="Details, when the line could not be used as written.")

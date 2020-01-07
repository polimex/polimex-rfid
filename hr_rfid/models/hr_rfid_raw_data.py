from odoo import models, api, fields


data_types_selection = [
    ('barcode', 'Barcode'),
    ('card', 'Card'),
]


class RawData(models.Model):
    _name = 'hr.rfid.raw.data'
    _description = 'Raw Data'

    data_type = fields.Selection(
        data_types_selection,
        string='Data Type',
    )

    data = fields.Char(
        string='Data',
    )

    timestamp = fields.Datetime(
        string='Time the event/data was created',
    )

    receive_ts = fields.Datetime(
        string='Receive timestamp',
        default=fields.Datetime.now()
    )

    webstack_serial = fields.Char(
        string='Webstack serial',
    )

    security = fields.Char(
        string='Security',
    )

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = self.env['hr.rfid.raw.data']
        for vals in vals_list:
            if 'do_not_save' in vals and vals['do_not_save'] is True:
                continue

            records += super(RawData, self).create(vals)
        return records


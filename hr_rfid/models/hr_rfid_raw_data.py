from odoo import models, fields

import json


class RawData(models.Model):
    _name = 'hr.rfid.raw.data'
    _description = 'Raw Data'

    data = fields.Char(
        string='Data',
    )

    timestamp = fields.Datetime(
        string='Event/Data timestamp',
        help='Time the event/data was created',
    )

    receive_ts = fields.Datetime(
        string='Receive timestamp',
        default=fields.Datetime.now
    )

    identification = fields.Char(
        string='Webstack serial',
    )

    security = fields.Char(
        string='Security',
    )

    do_not_save = fields.Boolean(
        string='Save data?',
        help="Whether to save the data or not after it's been dealt with",
        default=False,
    )

    return_data = fields.Char(
        string='Return Data',
        help='What to return to the json request',
        default=json.dumps({'status': 200}),
    )

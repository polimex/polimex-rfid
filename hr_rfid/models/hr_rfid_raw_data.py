from odoo import models, fields

import json


class RawData(models.Model):
    _name = 'hr.rfid.raw.data'
    _description = 'RFID System Raw Data Storage'

    data = fields.Char(
        string='Raw Data',
        help='The complete raw data packet received from RFID devices. '
             'This includes card readings, sensor data, and system messages in their original format.',
    )

    timestamp = fields.Datetime(
        string='Event Time',
        help='When this event occurred at the RFID device (e.g., when a card was scanned). '
             'This may differ from the receive time due to network delays.',
    )

    receive_ts = fields.Datetime(
        string='Received At',
        help='When our system received this data from the RFID device. '
             'Compare with Event Time to identify communication delays.',
        default=fields.Datetime.now
    )

    identification = fields.Char(
        string='Device Serial',
        help='The serial number of the webstack (communication module) that sent this data. '
             'This identifies which device in your network generated the event.',
    )

    security = fields.Char(
        string='Security Token',
        help='Security verification data to ensure this message came from an authorized device. '
             'This helps prevent unauthorized access to your RFID system.',
    )

    do_not_save = fields.Boolean(
        string='Temporary Data',
        help='Check this box if this data should be processed but not permanently stored. '
             'Useful for routine heartbeat messages or temporary test data.',
        default=False,
    )

    return_data = fields.Char(
        string='Response Data',
        help='The response sent back to the RFID device after processing this data. '
             'Usually contains status codes or commands for the device.',
        default=json.dumps({'status': 200}),
    )

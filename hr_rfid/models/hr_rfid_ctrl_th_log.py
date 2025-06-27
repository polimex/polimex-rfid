from odoo import fields, models, api


class CtrlTemperatureAndHumidityLog(models.Model):
    _name = 'hr.rfid.ctrl.th.log'
    _description = 'Temperature and Humidity Reading History'
    _order = 'event_time desc, id'

    temperature = fields.Float(
        string='Temperature (°C)',
        help='The temperature reading at this point in time (in Celsius). '
             'These historical values help identify patterns and anomalies.',
        aggregator='avg',
    )
    humidity = fields.Float(
        string='Humidity (%)',
        help='The humidity reading at this point in time (as a percentage). '
             'Track changes over time to ensure optimal environmental conditions.',
        aggregator='avg',
    )
    th_id = fields.Many2one(
        string='Sensor',
        comodel_name='hr.rfid.ctrl.th',
        help='The temperature/humidity sensor that recorded this reading. '
             'Each log entry is linked to its source sensor for tracking.',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    event_time = fields.Datetime(
        string='Reading Time',
        help='The exact date and time when this temperature/humidity reading was taken. '
             'Use this to analyze environmental conditions over specific time periods.',
        default=lambda self: fields.Datetime.now(),
        index=True,
    )


from odoo import fields, models, api


class CtrlTemperatureAndHumidityLog(models.Model):
    _name = 'hr.rfid.ctrl.th.log'
    _description = 'Temperature and humidity log'
    _order = 'event_time desc, id'

    temperature = fields.Float(
        help='Current Temperature value',
        group_operator='avg',
    )
    humidity = fields.Float(
        help='Current Humidity value',
        group_operator='avg',
    )
    th_id = fields.Many2one(
        string='Sensor',
        comodel_name='hr.rfid.ctrl.th',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    event_time = fields.Datetime(
        string='Timestamp',
        help='Time the event triggered',
        default=lambda self: fields.Datetime.now(),
        index=True,
    )


from odoo import fields, models, api, _, SUPERUSER_ID


class CtrlTemperatureAndHumidity(models.Model):
    _name = 'hr.rfid.ctrl.th'
    _inherit = ['mail.thread']
    _description = 'Temperature and Humidity Sensor'

    active = fields.Boolean(
        default=True,
        tracking=True,
        help='When unchecked, this sensor will be hidden and stop recording data. '
             'You can reactivate it later without losing historical data.'
    )
    name = fields.Char(
        string='Sensor Name',
        help='Give this sensor a descriptive name (e.g., "Server Room Temperature", "Warehouse Humidity"). '
             'This name will appear in reports and alerts.',
        required=True,
        default='T&H Sensor'
    )
    uid = fields.Char(
        string='Serial Number',
        help='The unique serial number of this temperature/humidity sensor. '
             'This is set by the manufacturer and cannot be changed.',
    )
    internal_number = fields.Char(
        string='Internal ID',
        help='The internal identification number assigned by the controller. '
             'This is used for communication between the sensor and controller.',
        tracking=True
    )
    temperature = fields.Float(
        string='Current Temperature',
        help='The most recent temperature reading from this sensor (in Celsius). '
             'This value updates automatically when the sensor sends new data.',
        aggregator='avg',
        readonly=True,
    )
    humidity = fields.Float(
        string='Current Humidity',
        help='The most recent humidity reading from this sensor (as a percentage). '
             'This value updates automatically when the sensor sends new data.',
        aggregator='avg',
        readonly=True,
    )
    sensor_number = fields.Integer(
        string='Sensor Number',
        help='The position number of this sensor in the controller\'s sensor list. '
             'This is automatically assigned and cannot be changed.',
        required=True,
        readonly=True,
    )
    controller_id = fields.Many2one(
        string='Controller',
        comodel_name='hr.rfid.ctrl',
        help='The RFID controller that manages this temperature/humidity sensor. '
             'Each sensor must be connected to a controller to function.',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    door_id = fields.Many2one(
        string='Associated Door',
        comodel_name='hr.rfid.door',
        help='Link this sensor to a specific door to monitor its environmental conditions. '
             'This is useful for server rooms or sensitive areas.',
        ondelete='cascade',
        tracking=True
    )
    th_log_ids = fields.One2many(
        string='Sensor Logs',
        comodel_name='hr.rfid.ctrl.th.log',
        inverse_name='th_id',
        help='Historical temperature and humidity readings from this sensor. '
             'Use the "View Logs" button to see detailed history and trends.'
    )
    log_every_read = fields.Boolean(
        string='Log All Readings',
        tracking=True,
        default=False,
        help='Check this box to save every reading from the sensor, even if values haven\'t changed. '
             'Leave unchecked to save storage space by only recording when temperature or humidity changes. '
             'Enable this for critical areas requiring complete audit trails.'
    )

    def button_log(self):
        res = self.env.ref('hr_rfid.hr_rfid_ctrl_th_log_action').read()[0]
        res['name'] = _('Temperature and Humidity Log for {}').format(self.name)
        res['domain'] = [('th_id', '=', self.id)]

        return res

    def create_d1_temperature_cmd(self):
        commands = []
        for sensor in self.filtered(lambda s: s.uid):
            # Adding sensor from controller
            commands.append(
                self.env['hr.rfid.command'].with_user(SUPERUSER_ID).create([{
                    'webstack_id': sensor.controller_id.webstack_id.id,
                    'controller_id': sensor.controller_id.id,
                    'cmd': 'D1',
                    'card_number': sensor.uid,
                    'pin_code': sensor.internal_number,
                    'ts_code': int(sensor.active),
                    # 'rights_data': rights_data,
                    # 'rights_mask': rights_mask,
                }])
            )
        if len(commands) == 1:
            return commands[0]
        else:
            return commands

    def write(self, vals):
        update_dict = {}
        if 'temperature' in vals and vals['temperature'] != self.temperature:
            update_dict.update({'temperature': vals['temperature']})
        if 'humidity' in vals and vals['humidity'] != self.humidity:
            update_dict.update({'humidity': vals['humidity']})
        if update_dict and self.sensor_number == 0:
            if not ('temperature' in update_dict):
                update_dict.update({'temperature': self.temperature})
            if not ('humidity' in update_dict):
                update_dict.update({'humidity': self.humidity})
            update_dict.update({'th_id': self.id})
            self.env['hr.rfid.ctrl.th.log'].sudo().create(update_dict)
        res = super(CtrlTemperatureAndHumidity, self).write(vals)
        if 'active' in vals or 'internal_number' in vals:
            for s in self.filtered(lambda sensor: sensor.uid):
                s.create_d1_temperature_cmd()
        return res

    def write_log(self, timestamp, values: dict):
        self.ensure_one()
        update_dict = {}
        if 't' in values and (self.log_every_read or values['t'] != self.temperature):
            update_dict.update({'temperature': values['t']})

        if 'h' in values and (self.log_every_read or values['h'] != self.humidity):
            update_dict.update({'humidity': values['h']})

        if update_dict != {}:
            self.write(update_dict)
            update_dict.update({'th_id': self.id})
            update_dict.update({'event_time': timestamp})
            self.env['hr.rfid.ctrl.th.log'].sudo().create(update_dict)

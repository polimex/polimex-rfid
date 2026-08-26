import logging
import random
from datetime import datetime, time, timedelta

from odoo import fields, models, api, _, SUPERUSER_ID

_logger = logging.getLogger(__name__)

DEMO_TH_SEED = 20260826
DEMO_TH_READINGS_FLAG = 'hr_rfid.demo_th_readings_generated'


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
        # write_log already writes the reading down, with the time the device
        # reported rather than the moment it reached us - so when it is the
        # caller, this branch would file the SAME reading a second time under
        # a wrong timestamp. The branch stays for the other producer: the
        # 5-minute controller poll (hr_rfid_ctrl.py) writes the values
        # straight onto the sensor and has nothing else to record them.
        if (update_dict and self.sensor_number == 0
                and not self.env.context.get('th_reading_logged')):
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
            self.with_context(th_reading_logged=True).write(update_dict)
            update_dict.update({'th_id': self.id})
            update_dict.update({'event_time': timestamp})
            self.env['hr.rfid.ctrl.th.log'].sudo().create(update_dict)

    @api.model
    def _demo_generate_th_readings(self):
        """Fill the shipped demo sensor with two weeks of readings.

        The Environment menus (sensors and their log) are reachable from the
        app, so a demo that leaves them empty shows a feature that looks
        unimplemented. The readings go in through write_log - the same entry
        point the controller uses when it reports - so the demo exercises the
        real path rather than inserting rows behind it.

        Only invoked from the demo data <function> hook. Idempotent: an
        ir.config_parameter flag makes a demo reload a no-op. Deterministic:
        a fixed-seed RNG yields the same curve on every fresh install.
        """
        param = self.env['ir.config_parameter'].sudo()
        if param.get_param(DEMO_TH_READINGS_FLAG):
            return

        sensor = self.env.ref('hr_rfid.demo_th_sensor_server_room',
                              raise_if_not_found=False)
        if not sensor:
            return

        rng = random.Random(DEMO_TH_SEED)
        now = fields.Datetime.now()
        today = now.date()
        readings = 0
        # Every two hours for a fortnight: enough for the graph to show the
        # daily swing of a server room without burying the list view.
        for day_offset in range(13, -1, -1):
            day = today - timedelta(days=day_offset)
            for hour in range(0, 24, 2):
                stamp = datetime.combine(day, time(hour, 0, 0))
                if stamp >= now:
                    continue
                # Coolest before dawn, warmest mid-afternoon, plus noise.
                swing = 1.6 * (1 - abs(hour - 15) / 12.0)
                temperature = round(21.5 + swing + rng.uniform(-0.4, 0.4), 1)
                humidity = round(43.0 - swing * 2 + rng.uniform(-1.5, 1.5), 1)
                sensor.write_log(stamp, {'t': temperature, 'h': humidity})
                readings += 1

        param.set_param(DEMO_TH_READINGS_FLAG, '1')
        _logger.info('Demo environment readings generated: %d readings over '
                     '14 days for sensor %s', readings, sensor.name)

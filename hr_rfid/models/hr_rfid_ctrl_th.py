from odoo import fields, models, api, _


class CtrlTemperatureAndHumidity(models.Model):
    _name = 'hr.rfid.ctrl.th'
    _description = 'Temperature and Humidity log'

    name = fields.Char(
        help='Sensor friendly name',
        required=True,
        default='T&H Sensor'
    )
    temperature = fields.Float(
        help='Current Temperature value',
        group_operator='avg',
        readonly=True,
    )
    humidity = fields.Float(
        help='Current Humidity value',
        group_operator='avg',
        readonly=True,
    )
    sensor_number = fields.Integer(
        required=True,
        readonly = True,
    )
    controller_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    door_id = fields.Many2one(
        comodel_name='hr.rfid.door',
        ondelete='cascade',
    )
    th_log_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.th.log',
        inverse_name='th_id'

    )

    def button_log(self):
        res = self.env.ref('hr_rfid.hr_rfid_ctrl_th_log_action').read()[0]
        res['name'] = _('Temperature and Humidity Log for {}').format(self.name)
        res['domain'] = [('th_id', '=', self.id)]

        return res


    def write(self, vals):
        update_dict = {}
        if 'temperature' in vals and vals['temperature'] != self.temperature:
            update_dict.update({'temperature': vals['temperature']})
        if 'humidity' in vals and vals['humidity'] != self.humidity:
            update_dict.update({'humidity': vals['humidity']})
        if update_dict:
            if not ('temperature' in update_dict):
                update_dict.update({'temperature': self.temperature})
            if not ('humidity' in update_dict):
                update_dict.update({'humidity': self.humidity})
            update_dict.update({'th_id': self.id})
            self.env['hr.rfid.ctrl.th.log'].sudo().create(update_dict)
        return super(CtrlTemperatureAndHumidity, self).write(vals)




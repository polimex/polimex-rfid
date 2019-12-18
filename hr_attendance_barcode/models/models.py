# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from functools import reduce

import json


class Event(models.Model):
    _name = 'hr.barcode.event'
    _description = 'Barcode Event'

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        required=True,
    )

    device = fields.Selection(
        [ ('uart0', 'Uart0'), ('uart2', 'Uart2') ],
        string='Device',
        required=True,
    )

    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
    )

    barcode_id = fields.Many2one(
        'hr.rfid.card',
        string='Barcode',
    )

    raw_barcode = fields.Char(
        string='Barcode',
    )

    @api.multi
    def _check_employee_attendance(self):
        for ev in self:
            barcode = ev.barcode_id.number if ev.barcode_id else ev.raw_barcode
            emps = self.env['hr.employee'].search([ ('barcode', '=', barcode) ])
            emps.attendance_action_change_with_date(ev.timestamp)

    @api.constrains('barcode_id', 'raw_barcode')
    def _check_bc(self):
        for bc in self:
            if not bc.barcode_id and (bc.raw_barcode == '' or not bc.raw_barcode):
                raise exceptions.ValidationError('Barcode must be set.')

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = super(Event, self).create(vals_list)
        records._check_employee_attendance()
        return records


class RawDataInherit(models.Model):
    _inherit = 'hr.rfid.raw.data'

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        vals_in_js = [ 'serial', 'security', 'events' ]
        vals_in_evs = [ 'hardware', 'type', 'timestamp', 'data', 'where' ]

        barcode_event_hw = 2

        # TODO Differentiate between cards and barcodes. Hint: It's the "type" value in the event object

        def vals_in_object(_vals, _obj):
            return reduce(lambda a, b: a and (b in _obj), _vals, True)

        for vals in vals_list:
            if 'data' not in vals or 'timestamp' not in vals \
                    or 'identification' not in vals or 'security' not in vals:
                continue

            js = json.loads(vals['data'])

            correct_vals = vals_in_object(vals_in_js, js)
            if not correct_vals:
                continue

            for ev in js['events']:
                if not vals_in_object(vals_in_evs, ev) or ev['hardware'] != barcode_event_hw:
                    continue

                ws = self.env['hr.rfid.webstack'].search([ ('serial', '=', str(js['identification'])) ])
                if not ws:
                    # TODO Is this correct? Continue if there is not webstack from that serial?
                    continue

                if ws.key != vals['security']:
                    # TODO Is this correct? Continue if the webstack's key is wrong?
                    continue

                ev_obj = {
                    'webstack_id': ws.id,
                    'device': 'uart0' if ev['where'] == 0 else 'uart2',
                    'timestamp': vals['timestamp'],
                }

                raw_bc = ev['data']
                bc = self.env['hr.rfid.card'].search([
                    ('number', '=', raw_bc),
                    ('card_type', '=', self.env['hr.rfid.card.type'].ref('hr_rfid_card_type_barcode').id),
                ])
                if not bc:
                    ev_obj['raw_barcode'] = raw_bc
                else:
                    ev_obj['barcode_id'] = bc.id

                self.env['hr.barcode.event'].create([ev_obj])

        return super(RawDataInherit, self).create(vals_list)

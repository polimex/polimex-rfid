from odoo import fields, models, api, _
from datetime import datetime, timedelta, date, time, timezone
from odoo.exceptions import UserError, ValidationError
import pytz
import requests

import logging

_logger = logging.getLogger(__name__)


class RfidPmsBaseCardEncodeMsgWiz(models.TransientModel):
    _name = 'rfid_pms_base.message_wiz'

    message = fields.Html()


class RfidPmsBaseCardEncodeWiz(models.TransientModel):
    _name = 'rfid_pms_base.card_encode_wiz'

    def _compute_mode(self):
        if self.env.context.get('current', False):
            return 'current'
        elif self.env.context.get('new', False):
            return 'new'
        elif self.env.context.get('stuff', False):
            return 'stuff'
        else:
            return 'read'

    def _get_room_id(self):
        # return self._context.get("active_id")
        if not self.env.context.get('stuff', False):
            return self.env['rfid_pms_base.room'].browse(self._context.get("active_id", []))

    def _get_employee_id(self):
        # return self._context.get("active_id")
        if self.env.context.get('stuff', False):
            return self.env['hr.employee'].browse(self._context.get("active_id", []))

    def _get_reservation_seq(self):
        if self.env.context.get('new', False):
            return self.env['ir.sequence'].next_by_code('base.pms.reservation')

    def _default_checkin(self):
        mode = self._compute_mode()
        if mode == 'new':
            return fields.Datetime.now()
        elif mode == 'current':
            return self.room_id.all_contact_ids[0].contact_id.hr_rfid_card_ids[0].activate_on

    def _default_checkout(self):
        mode = self._compute_mode()
        if mode == 'new':
            return datetime.combine(fields.Date.today() + timedelta(days=1), time(hour=9))
        elif mode == 'current':
            return self.room_id.all_contact_ids[0].contact_id.hr_rfid_card_ids[0].deactivate_on

    room_id = fields.Many2one(comodel_name='rfid_pms_base.room', default=_get_room_id)
    employee_id = fields.Many2one(comodel_name='hr.employee', default=_get_employee_id)
    reservation = fields.Char(default=_get_reservation_seq)
    checkin_date = fields.Datetime(
        string="Check In",
        default=_default_checkin,
    )
    checkout_date = fields.Datetime(
        string="Check Out",
        default=_default_checkout,
    )
    mode = fields.Selection(selection=[
        ('read', 'Read only'),
        ('new', 'New Reservation'),
        ('current', 'Current Reservation'),
        ('stuff', 'Stuff encoding'),
    ], default=_compute_mode)

    card_number = fields.Char(string='The card number', size=10, required=True)

    def read_card(self):
        if not self.encoder_id:
            raise UserError('No encoder for operation!')
        rdata = requests.get(self.encoder_id.ip + '/cards').json()
        _logger.debug('Read from encoder:\n{data}'.format(data=rdata))
        if 'status' not in rdata:
            raise UserError('Unknown response from Encoder.')
        if rdata['status'] == 'error':
            raise UserError('Put card on encoder and try again!')
        elif rdata['status'] == 'success':
            try:
                exp_tmp = datetime.fromtimestamp(rdata.get('validity_to'))
            except Exception as e:
                _logger.error('Received Validity to {d} is not correct. May be old card. Error: {e}'.format(e=e,
                                                                                                            d=rdata.get(
                                                                                                                'validity_to')))
                exp_tmp = datetime.now()
            room = rdata.get('room')
            group = rdata.get('group_id')
            self.card_id = self.env['sch_encoder.card'].search([('uid', '=', rdata.get('uid'))])
            employee_id = self.card_id.employee_id or None
            if room != 0:
                c_type = '<strong>GUEST</strong> Card '
                r_num = 'Room: {r}'.format(r=room)
            else:
                c_type = '<strong>STUFF ({name}) </strong> card'.format(
                    name=employee_id.name if employee_id else 'Unknown employee')
                group_id = self.env['sch_encoder.group'].search([('number', '=', group)], limit=1)
                r_num = 'Group: ' + group_id.name if group_id else 'Unknown({n})'.format(n=group)
            tz = pytz.timezone(self.env.user.tz)
            dt_format = '%Y-%m-%d %H:%M:%S'
            # dt_format = self.env.user.lang_id.date_format+' '+self.env.user.lang_id.time_format
            card_data = '{valid} VALID<br/>Card Number: {uid}<br/> {rn}<br/> Validity: {dfrom} to {exp}'.format(
                valid=c_type + ' <strong>IS</strong>' if exp_tmp > datetime.now() else c_type + ' <strong>IS NOT</strong>',
                uid=rdata.get('uid'),
                rn=r_num,
                exp=datetime.fromtimestamp(exp_tmp.timestamp(), tz).strftime(dt_format),
                dfrom=datetime.fromtimestamp(rdata.get('validity_from'), tz).strftime(dt_format)
            )
            if not self.card_id:
                vals = {
                    'name': 'Autogenerated {num}'.format(num=rdata.get('uid')),
                    'uid': rdata.get('uid'),
                    'valid_from': datetime.fromtimestamp(rdata.get('validity_from')),
                    'valid_to': exp_tmp,
                }
                _logger.info('New card: ' + str(vals))
                self.card_id = self.env['sch_encoder.card'].sudo().create([vals])
            return {
                'type': 'ir.actions.act_window',
                "name": "Card data",
                "res_model": "sch_encoder.message_wiz",
                "view_type": "form",
                "view_mode": "form",
                "target": "new",
                "context": {"default_message": card_data},
            }
        else:
            raise UserError(rdata.get('error', 'Unknown error!'))
        return {
            "type": "ir.actions.do_nothing",
        }

    def write_card(self):
        if (self.checkout_date - self.checkin_date) < timedelta(seconds=1):
            raise UserError(_('Wrong validity interval'))
        if not self.room_id:
            raise UserError(_('Please select a room'))
        if not self.card_number:
            raise UserError(_('Please scan a card'))
        if (self.checkout_date - self.checkin_date) > timedelta(days=30):
            raise UserError(_('The period for this card is more than 30 days'))

        data = {
            'validity_to': int(self.checkout_date.timestamp()),
            'validity_from': int(self.checkin_date.timestamp()),
        }
        card_number = ('0000000000' + self.card_number)[-10:]

        _logger.debug('Data for encode:\n{data}'.format(data=data))

        existing_card = self.env['hr.rfid.card'].with_context(active_test=False).search([('number', '=', card_number)])
        if existing_card:
            if (not existing_card.active) or existing_card.contact_id:
                existing_card.unlink()
            else:
                raise UserError(_('Card already in use for {}').format(existing_card.employee_id.name))

        count = len(self.room_id.all_contact_ids)
        if not self.reservation:
            if count > 0:
                parent = self.room_id.all_contact_ids[0].contact_id.parent_id
            else:
                parent = self.env['res.partner'].create({"name": self._get_reservation_seq()})
        else:
            parent = self.env['res.partner'].create({"name": self.reservation})
            if self.room_id.all_contact_ids:
                self.room_id.all_contact_ids.contact_id.hr_rfid_card_ids.unlink()
                self.room_id.all_contact_ids.contact_id.hr_rfid_access_group_ids.unlink()

        res_guest_id = self.env['res.partner'].create(
            {
                "name": _(f'Guest {count+1} for ') + parent.name,
                "parent_id": parent.id,
                'hr_rfid_card_ids': [(0, 0, {
                    'number': card_number,
                    # 'contact_id': res_guest_id.id,
                    'activate_on': self.checkin_date,
                    'deactivate_on': self.checkout_date,
                })],
                'hr_rfid_access_group_ids': [(0,0, {
                    'access_group_id': self.room_id.access_group_id.id,
                    # 'contact_id':
                    'expiration': self.checkout_date,
                })]

            }
        )

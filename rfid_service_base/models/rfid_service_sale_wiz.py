import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from datetime import datetime, timedelta, date, time, timezone
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_cron import _intervalTypes
from odoo.addons.resource.models.resource import float_to_time
from pytz import timezone, UTC
import requests

import logging

_logger = logging.getLogger(__name__)


class RfidServiceBaseSaleWiz(models.TransientModel):
    _name = 'rfid.service.sale.wiz'
    _description = 'Base RFID Service Sale Wizard'
    _inherit = ['balloon.mixin']

    def _get_service_id(self):
        return self.env['rfid.service'].browse(self._context.get("active_id", []))

    def _get_service_visits(self):
        return self._get_service_id().visits

    def _get_service_sale_seq(self):
        return self.env['ir.sequence'].next_by_code('base.rfid.service')

    def _default_start(self):
        dt = datetime.combine(fields.Date.today(),
                                float_to_time(self._get_service_id().time_interval_start))
        return pytz.timezone(self.env.user.tz).localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
        # return dt.replace(tzinfo=pytz.timezone(self.env.user.tz)).astimezone(pytz.UTC).replace(tzinfo=None)
        # return timezone(self.env.user.tz).localize(dt).astimezone(UTC).replace(tzinfo=None)

    def _get_default_card_number(self):
        num = ''
        if self._get_service_id().generate_barcode_card:
            hex, num = self.env['hr.rfid.card'].create_bc_card()
        return num

    service_id = fields.Many2one(comodel_name='rfid.service', default=_get_service_id)
    fixed_time = fields.Boolean(related='service_id.fixed_time', readonly=True)
    generate_barcode_card = fields.Boolean(related='service_id.generate_barcode_card')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        help='The value will be generated automatic if empty!'
    )
    email = fields.Char()
    mobile = fields.Char()
    start_date = fields.Datetime(
        string="Service start",
        default=_default_start,
    )
    end_date = fields.Datetime(
        string="Service end",
        compute='_compute_end_date',
        inverse='_inverse_end_date'
    )
    end_date_manual = fields.Datetime(
        string="Custom Service end",
    )
    card_number = fields.Char(
        string='The card number', size=10,
        required=True,
        default=_get_default_card_number)
    visits = fields.Integer(related='service_id.visits')

    def _inverse_end_date(self):
        self.end_date_manual = self.end_date

    @api.onchange('start_date')
    def _compute_end_date(self):
        if self.fixed_time or not self.end_date:
            dt = datetime.combine((self.start_date + _intervalTypes[self._get_service_id().time_interval_type](
                self._get_service_id().time_interval_number)).date(),
                                  float_to_time(self._get_service_id().time_interval_end))
            dt = pytz.timezone(self.env.user.tz).localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
            if dt < fields.Datetime.now():
                dt = dt + relativedelta(days=1)
                self.start_date = self.start_date + relativedelta(days=1)
            self.end_date = self.end_date_manual or dt
        else:
            self.end_date = self.end_date

    def _gen_partner(self, partner_id=None):
        if partner_id is None:
            partner_id = self.env['res.partner'].create({
                'name': '%s (%s)' % (self._get_service_sale_seq(), self.service_id.name),
                'company_id': self.service_id.company_id.id,
                'mobile': self.mobile,
                'email': self.email,
                'parent_id': self.service_id.parent_id,
            })
        access_group_contact_rel = self.env['hr.rfid.access.group.contact.rel'].sudo().search([
            ('access_group_id', '=', self.service_id.access_group_id.id),
            ('contact_id', '=', partner_id.id),
        ])
        if access_group_contact_rel:
            if not access_group_contact_rel.expiration or access_group_contact_rel.expiration <= fields.Datetime.now():
                access_group_contact_rel.sudo().write({
                    'activate_on': self.start_date,
                    'expiration': self.end_date,
                    'permitted_visits': self.visits,
                    'visits_counting': self.visits > 0,
                    'write_uid': self.env.user.id,
                })
            else:
                raise UserError(_('The partner have valid service for this period!'))
        else:
            access_group_contact_rel = self.env['hr.rfid.access.group.contact.rel'].sudo().create({
                'access_group_id': self.service_id.access_group_id.id,
                'contact_id': partner_id.id,
                'activate_on': self.start_date,
                'expiration': self.end_date,
                'permitted_visits': self.visits,
                'visits_counting': self.visits > 0,
                'create_uid': self.env.user.id,
                'write_uid': self.env.user.id,
            })
        card_id = self.env['hr.rfid.card'].sudo().create({
            'contact_id': partner_id.id,
            'number': self.card_number,
            'card_type': self.service_id.card_type.id,
            'card_reference': '%s (%s)' % (partner_id.name, self.service_id.name),
            'company_id': self.service_id.company_id.id,
            'activate_on': self.start_date,
            'deactivate_on': self.end_date,
            'create_uid': self.env.user.id,
            'write_uid': self.env.user.id,
        })
        return partner_id, access_group_contact_rel, card_id
    def email_card(self):
        if not self.email and not self.partner_id :
            raise UserError(_('Please fill the e-mail in the form'))
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        return self.partner_id.action_send_badge_email()

    def print_card(self):
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        return self.env.ref('hr_rfid.action_report_res_partner_foldable_badge').report_action(self.partner_id)

    def write_card(self):
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        # return self.balloon_success(
        #     title=_('Successful activation of %s' % self.service_id.name),
        #     message='%s service is registered for %s with card %s' % (sale_id.name, partner_id.name, card_id.number)
        # )

    def _write_card(self):
        if not self.card_number:
            raise UserError(_('Please scan a card'))
        if self.end_date < fields.Datetime.now():
            raise UserError(_('The period for this sale finish in the past. Please check details again!'))
        if not self.service_id.access_group_id.door_ids:
            raise UserError(_('The access group for this service have no any doors. Please fix it and try again!'))
        if not self.partner_id:
            self.partner_id, access_group_contact_rel, card_id = self._gen_partner()
        else:
            self.partner_id, access_group_contact_rel, card_id = self._gen_partner(self.partner_id)
        sale_id = self.env['rfid.service.sale'].create({
            'name': self.partner_id.name,
            'service_id': self.service_id.id,
            'partner_id': self.partner_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'card_id': card_id.id,
            'access_group_contact_rel': access_group_contact_rel.id
        })
        return sale_id, self.partner_id, access_group_contact_rel, card_id

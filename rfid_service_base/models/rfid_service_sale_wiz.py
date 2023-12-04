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

    def _get_extend_id(self):
        extend_id = self._context.get('extend', None)
        if extend_id is not None:
            return self.env['rfid.service.sale'].browse(extend_id)
        else:
            return None

    def _get_service_id(self):
        extend_id = self._get_extend_id()
        return extend_id and extend_id.service_id or self.env['rfid.service'].browse(self._context.get("active_id", []))

    def _get_service_visits(self):
        return self._get_service_id().visits

    def _get_service_sale_seq(self):
        return self.env['ir.sequence'].next_by_code('base.rfid.service')

    def _get_partner_id(self):
        extend_sale_id = self._get_extend_id()
        if extend_sale_id is not None:
            return extend_sale_id.partner_id
        else:
            return None

    def _default_start(self):
        def _calc_start(start_date=fields.Date.today()):
            dt = datetime.combine(start_date,
                                  float_to_time(service_id.time_interval_start))
            return pytz.timezone(self.env.user.tz).localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)

        service_id = self._get_service_id()
        extend_sale_id = self._get_extend_id()
        if extend_sale_id is not None:
            if fields.Datetime.now() < extend_sale_id.start_date:
                # "before"
                return _calc_start(extend_sale_id.end_date.date())
            elif extend_sale_id.start_date <= fields.Datetime.now() <= extend_sale_id.end_date:
                # "in"
                return _calc_start(extend_sale_id.end_date.date())
            else:
                # "after"
                return _calc_start()
        else:
            return _calc_start()

    def _get_default_card_number(self):
        extend_sale_id = self._get_extend_id()
        if extend_sale_id is not None:
            return extend_sale_id.card_id.number
        else:
            num = ''
            if self._get_service_id().generate_barcode_card:
                hex, num = self.env['hr.rfid.card'].create_bc_card()
            return num

    extend_sale_id = fields.Many2one(
        comodel_name='rfid.service.sale',
        default=_get_extend_id,
        readonly=True
    )
    ext_start_date = fields.Datetime(
        string="Old start",
        related='extend_sale_id.start_date',
        readonly=True
    )
    ext_end_date = fields.Datetime(
        string="Old end",
        related='extend_sale_id.end_date',
        readonly=True
    )
    service_id = fields.Many2one(comodel_name='rfid.service', default=_get_service_id)
    fixed_time = fields.Boolean(related='service_id.fixed_time', readonly=True)
    generate_barcode_card = fields.Boolean(related='service_id.generate_barcode_card')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain=["&", ("is_company", "=", False), ("type", "=", "contact")],
        help='The value will be generated automatic if empty!',
        default=_get_partner_id
    )
    email = fields.Char(
        compute='_compute_partner_contact',
        readonly=False,
        store=True
    )
    mobile = fields.Char(
        compute='_compute_partner_contact',
        readonly=False,
        store=True
    )
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

    @api.onchange('partner_id')
    def _compute_partner_contact(self):
        self.mobile = self.partner_id.mobile
        self.email = self.partner_id.email

    @api.onchange('start_date', 'service_id')
    def _compute_end_date(self):
        # if self.fixed_time or not self.end_date:
        #     dt = datetime.combine((self.start_date + _intervalTypes[self._get_service_id().time_interval_type](
        #         self._get_service_id().time_interval_number)).date(),
        #                           float_to_time(self._get_service_id().time_interval_end))
        #     dt = pytz.timezone(self.env.user.tz).localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
        service_id = self.service_id or self._get_service_id()
        time_interval_type = service_id.time_interval_type
        time_interval_number = service_id.time_interval_number
        time_interval_end = service_id.time_interval_end
        if self.fixed_time or not self.end_date:
            new_date = self.start_date + _intervalTypes[time_interval_type](time_interval_number)
            new_time = float_to_time(time_interval_end)
            dt = datetime.combine(new_date.date(), new_time)
            user_tz = pytz.timezone(self.env.user.tz)
            dt = user_tz.localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
            if dt < fields.Datetime.now():
                dt = dt + relativedelta(days=1)
                self.start_date = self.start_date + relativedelta(days=1)
            self.end_date = self.end_date_manual or dt
        else:
            self.end_date = self.end_date

    def _gen_partner(self, partner_id=None):
        transaction_name = self._get_service_sale_seq()
        if partner_id is None:
            partner_id = self.env['res.partner'].create({
                'name': '%s (%s)' % (transaction_name, self.service_id.name),
                'company_id': self.service_id.company_id.id,
                'mobile': self.mobile,
                'email': self.email,
                'parent_id': self.service_id.parent_id,
            })
        else:
            partner_id.write({
                'mobile': self.mobile,
                'email': self.email,
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
        existing_card_id = self.env['hr.rfid.card'].sudo().with_context(test_active=False).search([
            ('number', '=', self.card_number),
        ])
        if existing_card_id and existing_card_id.contact_id != partner_id:
            raise UserError(
                _("The card (%s) is not related to this Customer (%s") % (self.card_number, partner_id.name)
            )
        if not existing_card_id:
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
        else:
            card_id = existing_card_id
            card_id.active = True

        return partner_id, access_group_contact_rel, card_id, transaction_name

    def email_card(self):
        if not self.email and not self.partner_id:
            raise UserError(_('Please fill the e-mail in the form'))
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        return self.partner_id.action_send_badge_email()

    def print_card(self):
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        return self.env.ref('hr_rfid.action_report_res_partner_foldable_badge').report_action(self.partner_id)

    def write_card(self):
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        if self.extend_sale_id is not None:
            return self.env["ir.actions.act_window"]._for_xml_id("rfid_service_base.hr_rfid_service_sale_action")
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
            self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner()
        else:
            self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner(self.partner_id)
        sale_id = self.env['rfid.service.sale'].create({
            'name': '%s (%s)' % (transaction_name, self.service_id.name),
            'service_id': self.service_id.id,
            'partner_id': self.partner_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'card_id': card_id.id,
            'access_group_contact_rel': access_group_contact_rel.id
        })
        if self.extend_sale_id is not None:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            link = f"{base_url}/web#id={sale_id.id}&model=rfid.service.sale&view_type=form"
            message = _("This Sale is extended by <a href='%s'>Sale %s</a>", link, sale_id.display_name)
            self.extend_sale_id.message_post(body=message, message_type='comment')

            link = f"{base_url}/web#id={self.extend_sale_id.id}&model=rfid.service.sale&view_type=form"
            message = _("This Sale extends <a href='%s'>Sale %s</a>", link, self.extend_sale_id.display_name)
            sale_id.message_post(body=message, message_type='comment')

        return sale_id, self.partner_id, access_group_contact_rel, card_id

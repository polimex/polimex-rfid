import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from datetime import datetime, timedelta, date, time, timezone
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_cron import _intervalTypes
from odoo.tools.date_utils import float_to_time
from pytz import timezone, UTC
import requests

import logging

_logger = logging.getLogger(__name__)


class RfidServiceBaseSaleWiz(models.TransientModel):
    _name = 'rfid.service.sale.wiz'
    _description = 'Base RFID Service Sale Wizard'
    _inherit = ['balloon.mixin']

    def _get_service_sale_seq(self):
        return self.env['ir.sequence'].next_by_code('base.rfid.service')

    def _site_tz(self):
        """The clock the site runs on - the one the customer reads."""
        return pytz.timezone(self.env.user.tz or self.env.company.partner_id.tz
                             or 'UTC')

    def _to_utc(self, naive_local):
        return self._site_tz().localize(naive_local).astimezone(
            pytz.UTC).replace(tzinfo=None)

    def _local_date(self, moment=None):
        """The date it is AT THE SITE right now (or at the given moment)."""
        moment = moment or fields.Datetime.now()
        return pytz.UTC.localize(moment).astimezone(self._site_tz()).date()

    def _opens_on(self, local_day):
        """When the service opens on that day of the site's calendar."""
        return self._to_utc(datetime.combine(
            local_day, float_to_time(self.service_id.time_interval_start)))

    def _calc_start(self):
        """When the visit being sold begins.

        Two things here were wrong, and both put the period in the PAST:

        * the day was a DEFAULT ARGUMENT - ``start_date=fields.Date.today()`` -
          which Python evaluates ONCE, when the module is imported. A server
          that had been up for a day or two therefore sold every visit against
          the date it BOOTED on; the "+1 day" correction downstream covers one
          day, so from the second day on the till simply refused the card with
          "the period ends in the past". Nothing about the sale itself said
          which day it was using, which is why it looked random.
        * the day was taken in UTC, while opening hours are the SITE's. For a
          third of the day in summer here the two are different dates.
        """
        if not self.fixed_time:
            return fields.Datetime.now()
        extend_sale_id = self.extend_sale_id
        if extend_sale_id and fields.Datetime.now() <= extend_sale_id.end_date:
            # Extending a pass that is still running (or not started yet):
            # the new period picks up on the day the old one ends.
            return self._opens_on(self._local_date(extend_sale_id.end_date))
        return self._opens_on(self._local_date())

    def _calc_end(self, start_date=None):
        service_id = self.service_id
        time_interval_type = service_id.time_interval_type
        time_interval_number = service_id.time_interval_number
        time_interval_end = service_id.time_interval_end

        start = self.start_date or start_date
        if self.fixed_time:
            # The last day of the pass, and the hour the site closes on it -
            # both read on the SITE's calendar. Taken from the UTC date, a pass
            # sold in the evening ended on the wrong day.
            last_local_day = (self._local_date(start)
                              + _intervalTypes[time_interval_type](time_interval_number))
            return self._to_utc(datetime.combine(
                last_local_day, float_to_time(time_interval_end)))
        return start + _intervalTypes[time_interval_type](time_interval_number)

    extend_sale_id = fields.Many2one(
        comodel_name='rfid.service.sale',
        readonly=True,
        help="When set, the wizard runs in Extend mode — it adds time to the linked sale instead of creating a new one. Populated automatically from the Extend action on the existing sale.",
    )
    ext_start_date = fields.Datetime(
        string="Old start",
        related='extend_sale_id.start_date',
        readonly=True,
        help="Original start date of the sale being extended (shown for reference).",
    )
    ext_end_date = fields.Datetime(
        string="Old end",
        related='extend_sale_id.end_date',
        readonly=True,
        help="Original end date of the sale being extended (shown for reference). The new end below replaces it on confirmation.",
    )
    service_id = fields.Many2one(
        comodel_name='rfid.service',
        help="Catalog entry from which the card inherits its access group, time window and card type. Set automatically when the wizard is opened from a service.",
    )
    fixed_time = fields.Boolean(
        related='service_id.fixed_time',
        readonly=True,
        help="Mirrors the service's Fixed Time flag — when true, the end date snaps to a fixed daily cut-off instead of a rolling interval.",
    )
    generate_barcode_card = fields.Boolean(
        related='service_id.generate_barcode_card',
        readonly=True,
        help="Mirrors the service flag — when true, the wizard auto-generates a printable barcode instead of expecting a scanned RFID number.",
    )
    parent_id = fields.Many2one(
        comodel_name='res.partner',
        related='service_id.parent_id',
        readonly=True,
        help="Parent partner the new visitor contact will be filed under (inherited from the service template).",
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain=["&", ("is_company", "=", False), ("type", "=", "contact")],
        check_company=True,
        help='The value will be generated automatic if empty!',
    )
    email = fields.Char(
        compute='_compute_partner_contact',
        readonly=False,
        store=True,
        help="Visitor email address. Pre-filled from the selected partner; editing here also updates the partner record on confirmation.",
    )
    mobile = fields.Char(
        compute='_compute_partner_contact',
        readonly=False,
        store=True,
        help="Visitor mobile/phone number. Pre-filled from the selected partner; editing here also updates the partner's phone field on confirmation (in Odoo 19 mobile was merged into phone).",
    )
    start_date = fields.Datetime(
        string="Service start",
        compute='_onchange_service_id',
        readonly=False,
        store=True,
        help="Moment the card becomes active. Defaults to a calculated start based on the service's time interval, but you can override it.",
    )
    end_date = fields.Datetime(
        string="Service end",
        compute='_onchange_start_date',
        readonly=False,
        store=True,
        help="Moment the card stops working. Calculated from start + the service's time interval; for Fixed Time services it snaps to the daily cut-off.",
    )
    card_number = fields.Char(
        string='The card number', size=10,
        required=True,
        help="The RFID number or generated barcode the visitor will carry. For RFID services, type or scan the printed number; for barcode services, the value is generated automatically.",
    )
    visits = fields.Integer(
        related='service_id.visits',
        help="Mirrors the visits-per-card limit from the service template — informational only, the wizard does not let you override it.",
    )

    # def _inverse_end_date(self):
    #     self.end_date_manual = self.end_date

    @api.onchange('partner_id')
    def _compute_partner_contact(self):
        # `mobile` was merged into `phone` in Odoo 19; res.partner no longer
        # exposes a separate mobile field. The wizard keeps its own
        # `self.mobile` field for the UI label but mirrors the partner's
        # `phone` value here.
        self.mobile = self.partner_id.phone
        self.email = self.partner_id.email

    @api.onchange('service_id')
    @api.depends('service_id')
    def _onchange_service_id(self):
        calc_start = self._calc_start()
        calc_end = self._calc_end(start_date=calc_start)
        if (calc_end < fields.Datetime.now()) or (self.extend_sale_id and self.ext_end_date > calc_start):
            calc_end = calc_end + relativedelta(days=1)
            calc_start = calc_start + relativedelta(days=1)
        # self.write({
        #     'start_date': calc_start,
        #     'end_date': calc_end
        # })
        if calc_end < calc_start:
            calc_end = calc_start
        self.start_date = calc_start
        self.end_date = calc_end

    @api.onchange('start_date')
    @api.depends('start_date')
    def _onchange_start_date(self):
        calc_end = self._calc_end()
        if calc_end < self.start_date:
            calc_end = self.start_date
        self.end_date = calc_end

    def _gen_partner(self, partner_id=None, start_date=None, end_date=None):
        transaction_name = self._get_service_sale_seq()
        access_group_contact_rel = self.env['hr.rfid.access.group.contact.rel']
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': transaction_name,
                'company_id': self.service_id.company_id.id,
                'phone': self.mobile,
                'email': self.email,
                'parent_id': self.parent_id.id,
            })
        else:
            if partner_id.phone != self.mobile or partner_id.email != self.email:
                partner_id.write({
                    'phone': self.mobile,
                    'email': self.email,
                })
            access_group_contact_rel = self.env['hr.rfid.access.group.contact.rel'].sudo().search([
                ('access_group_id', '=', self.service_id.access_group_id.id),
                ('contact_id', '=', partner_id.id),
            ])
        for rel in access_group_contact_rel:
            if not rel.expiration:
                raise UserError(_('The partner have valid service for unlimited period!'))
            if (self.start_date < rel.expiration < self.end_date) and rel.state:
                raise UserError(_('The partner have valid service for this period!'))

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
        existing_card_id = self.env['hr.rfid.card'].sudo().with_context(active_test=False).search([
            ('number', '=', self.card_number),
        ])
        if existing_card_id.employee_id:
            raise UserError(
                _("The card %s is already used by employee %s") % (self.card_number, existing_card_id.employee_id.name)
            )
        if existing_card_id and existing_card_id.contact_id != partner_id:
            if existing_card_id.active:
                raise UserError(
                    _("The card %s is already used by partner %s") % (self.card_number, existing_card_id.contact_id.name)
                )
            else:
                existing_card_id.contact_id = partner_id.id
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
            existing_card_id.sudo().write({
                'card_reference': '%s (%s)' % (partner_id.name, self.service_id.name),
                'company_id': self.service_id.company_id.id,
                'activate_on': min( self.start_date, existing_card_id.activate_on),
                'deactivate_on': max( self.end_date, existing_card_id.deactivate_on),
                'write_uid': self.env.user.id,
            })
            card_id = existing_card_id
            # card_id.active = True

        return partner_id, access_group_contact_rel, card_id, transaction_name

    def email_card(self):
        if not self.email and not self.partner_id:
            raise UserError(_('Please fill the e-mail in the form'))
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        
        # Get the email compose action
        template = self.service_id.mail_template_id
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='res.partner',
            default_res_ids=self.partner_id.ids,
            default_partner_ids=[self.partner_id.id],
            default_use_template=bool(template),
            default_template_id=template and template.id,
            default_composition_mode='comment',
            custom_layout="mail.mail_notification_light",
        )
        
        email_action = {
            'name': _('Send Badge - Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        
        # Add close on report download behavior
        email_action.update({'close_on_report_download': True})
        
        return email_action

    def print_card(self):
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        # Use the print template from the service if configured, otherwise use default
        if self.service_id.print_template_id:
            report_action = self.service_id.print_template_id.report_action(self.partner_id)
        else:
            report_action = self.env.ref('hr_rfid.action_report_res_partner_foldable_badge').report_action(self.partner_id)
        
        # Update the action to close the wizard after download
        report_action.update({'close_on_report_download': True})
        
        return report_action

    def write_card(self):
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        if self.extend_sale_id:
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
            raise UserError(_(
                'The period for this sale ends in the past: it runs until '
                '%(end)s, and it is now %(now)s (%(tz)s). Check the dates '
                'and try again.',
                end=fields.Datetime.context_timestamp(self, self.end_date),
                now=fields.Datetime.context_timestamp(
                    self, fields.Datetime.now()),
                tz=self.env.user.tz or 'UTC',
            ))
        if not self.sudo().service_id.access_group_id.door_ids:
            raise UserError(_('The access group for this service have no any doors. Please fix it and try again!'))
        # if not self.partner_id:
        #     self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner(
        #         start_date=self.start_date, end_date=self.end_date)
        # else:
        #     self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner(self.partner_id,
        self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner(self.partner_id,
                                                                                                 start_date=self.start_date,
                                                                                                 end_date=self.end_date)
        sale_id = self.env['rfid.service.sale'].sudo().create({
            'name': '%s (%s)' % (transaction_name, self.service_id.name),
            'service_id': self.service_id.id,
            'partner_id': self.partner_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'card_id': card_id.id,
            # create_uid / write_uid are auto-managed by Odoo — don't set them
            # manually, especially not with a recordset value (Odoo 19 rejects
            # `res.users` recordsets where an Integer FK is expected).
            'access_group_contact_rel': access_group_contact_rel.id
        })
        sale_id.sudo().message_subscribe(partner_ids=[self.partner_id.id])
        if self.extend_sale_id:
            # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            # link = f"{base_url}/web#id={sale_id.id}&model=rfid.service.sale&view_type=form"
            link = f"/web#id={sale_id.id}&model=rfid.service.sale&view_type=form"
            message = _("This Sale is extended by <a href='%s'>Sale %s</a>", link, sale_id.display_name)
            self.extend_sale_id.sudo().message_post(body=message, message_type='comment')

            # link = f"{base_url}/web#id={self.extend_sale_id.id}&model=rfid.service.sale&view_type=form"
            link = f"/web#id={self.extend_sale_id.id}&model=rfid.service.sale&view_type=form"
            message = _("This Sale extends <a href='%s'>Sale %s</a>", link, self.extend_sale_id.display_name)
            sale_id.sudo().message_post(body=message, message_type='comment')

        return sale_id, self.partner_id, access_group_contact_rel, card_id

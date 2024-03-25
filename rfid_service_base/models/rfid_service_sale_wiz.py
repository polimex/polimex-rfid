import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_cron import _intervalTypes
from odoo.addons.resource.models.resource import float_to_time
from datetime import datetime, timedelta, date, time, timezone

import logging

_logger = logging.getLogger(__name__)


class RfidServiceBaseSaleWiz(models.TransientModel):
    _name = 'rfid.service.sale.wiz'
    _description = 'Base RFID Service Sale Wizard'
    _inherit = ['balloon.mixin']

    def _get_service_sale_seq(self):
        return self.env['ir.sequence'].next_by_code('base.rfid.service')

    def _calc_start(self):
        service_id = self.service_id
        extend_sale_id = self.extend_sale_id
        if extend_sale_id:
            if fields.Datetime.now() < extend_sale_id.start_date:
                # "before"
                return service_id.calc_start(extend_sale_id.end_date.date())
            elif extend_sale_id.start_date <= fields.Datetime.now() <= extend_sale_id.end_date:
                # "in"
                return service_id.calc_start(extend_sale_id.end_date.date())
            else:
                # "after"
                return service_id.calc_start()
        else:
            return service_id.calc_start()

    def _calc_end(self, start_date=None):
        return self.service_id.calc_end(start_date=start_date)

    extend_sale_id = fields.Many2one(
        comodel_name='rfid.service.sale',
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
    service_id = fields.Many2one(comodel_name='rfid.service')
    fixed_time = fields.Boolean(related='service_id.fixed_time', readonly=True)
    visits = fields.Integer(related='service_id.visits')
    service_type = fields.Selection(
        related='service_id.service_type',
    )

    generate_barcode_card = fields.Boolean(
        related='service_id.generate_barcode_card',
        readonly=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain=["&", ("is_company", "=", False), ("type", "=", "contact")],
        help='The value will be generated automatic if empty!',
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
        compute='_onchange_service_id',
        readonly=False,
        store=True
    )
    end_date = fields.Datetime(
        string="Service end",
        compute='_onchange_start_date',
        readonly=False,
        store=True
        # inverse='_inverse_end_date',
    )
    # end_date_manual = fields.Datetime(
    #     string="Custom Service end",
    # )
    card_number = fields.Char(
        string='The card number', size=10,
        required=True,
    )

    # def _inverse_end_date(self):
    #     self.end_date_manual = self.end_date

    @api.onchange('partner_id')
    def _compute_partner_contact(self):
        self.mobile = self.partner_id.mobile
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
        self.start_date = calc_start
        self.end_date = calc_end

    @api.onchange('start_date')
    @api.depends('start_date')
    def _onchange_start_date(self):
        self.end_date = self._calc_end()

    def _gen_partner(self, partner_id=None, start_date=None, end_date=None):
        transaction_name = self._get_service_sale_seq()
        access_group_contact_rel = self.env['hr.rfid.access.group.contact.rel']
        if partner_id is None:
            partner_id = self.env['res.partner'].create({
                'name': '%s (%s)' % (transaction_name, self.service_id.name),
                'company_id': self.service_id.company_id.id,
                'mobile': self.mobile,
                'email': self.email,
                'parent_id': self.service_id.parent_id.id,
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
        for rel in access_group_contact_rel:
            if not rel.expiration:
                raise UserError(_('The partner have valid service for unlimited period!'))
            if self.start_date < rel.expiration < self.end_date:
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
            existing_card_id.write({
                'deactivate_on': self.end_date,
            })
            card_id = existing_card_id
            # card_id.active = True

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
        # self._onchange_start_date()
        if not self.card_number:
            raise UserError(_('Please scan a card'))
        if self.end_date < fields.Datetime.now():
            raise UserError(_('The period for this sale finish in the past. Please check details again!'))
        if not self.service_id.access_group_id.door_ids:
            raise UserError(_('The access group for this service have no any doors. Please fix it and try again!'))
        if not self.partner_id:
            self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner(
                start_date=self.start_date, end_date=self.end_date)
        else:
            self.partner_id, access_group_contact_rel, card_id, transaction_name = self._gen_partner(self.partner_id,
                                                                                                     start_date=self.start_date,
                                                                                                     end_date=self.end_date)
        sale_id = self.env['rfid.service.sale'].create({
            'name': '%s (%s)' % (transaction_name, self.service_id.name),
            'service_id': self.service_id.id,
            'partner_id': self.partner_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'card_id': card_id.id,
            'access_group_contact_rel': access_group_contact_rel.id
        })
        sale_id.message_subscribe(partner_ids=[self.partner_id.id])
        if self.extend_sale_id:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            link = f"{base_url}/web#id={sale_id.id}&model=rfid.service.sale&view_type=form"
            message = _("This Sale is extended by <a href='%s'>Sale %s</a>", link, sale_id.display_name)
            self.extend_sale_id.message_post(body=message, message_type='comment')

            link = f"{base_url}/web#id={self.extend_sale_id.id}&model=rfid.service.sale&view_type=form"
            message = _("This Sale extends <a href='%s'>Sale %s</a>", link, self.extend_sale_id.display_name)
            sale_id.message_post(body=message, message_type='comment')

        return sale_id, self.partner_id, access_group_contact_rel, card_id

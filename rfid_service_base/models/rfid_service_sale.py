from datetime import timedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.hr_rfid.models.hr_rfid_event_user import HrRfidUserEvent

import logging
_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service.sale'
    _description = 'RFID Service Sales'
    _order = 'create_date desc'
    _inherit = "mail.thread"

    _sql_constraints = [
        ('check_duplicates', 'unique (service_id, start_date, end_date, partner_id)',
         _("Only one service for same period for given Customer!")),
    ]

    name = fields.Char(
        string='Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('rfid.service'),
    )
    service_id = fields.Many2one(
        comodel_name='rfid.service',
        required=True
    )
    start_date = fields.Datetime(
        string="Service start",
        required=True
    )
    end_date = fields.Datetime(
        string="Service end",
        required=True
    )

    state = fields.Selection(
        selection=[
            ('registered', 'Registered'),
            ('progress', 'Progress'),
            ('finished', 'Finished'),
            ('canceled', 'Canceled')
        ], compute='_compute_state', store=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='service_id.company_id'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Customer', check_company=True, index=True,
        domain=["&", ("is_company", "=", False), ("type", "=", "contact")],
        # domain="[('company_id', '=', company_id)]",
        help="Linked partner to this service sale")
    card_id = fields.Many2one(
        comodel_name='hr.rfid.card', check_company=True,
        # required=True
    )
    card_number = fields.Char(related='card_id.number')
    access_group_contact_rel = fields.Many2one(
        comodel_name='hr.rfid.access.group.contact.rel', check_company=True
    )
    visits = fields.Integer(
        string='Visits',
        related='access_group_contact_rel.visits_counter',
    )
    activated_on = fields.Datetime()

    # @api.depends('partner_id.hr_rfid_card_ids', 'partner_id.hr_rfid_access_group_ids')
    @api.depends('access_group_contact_rel')
    def _compute_state(self):
        for s in self:
            if not s.start_date:
                start_date = s.access_group_contact_rel.activate_on
                end_date = s.access_group_contact_rel.expiration
            else:
                start_date = s.start_date
                end_date = s.end_date
            state = 'registered'
            if start_date <= fields.Datetime.now() <= end_date:
                state = 'progress'
            elif (s.access_group_contact_rel.expiration-s.access_group_contact_rel.activate_on) == timedelta(seconds=1):
                state = 'canceled'
            elif end_date <= fields.Datetime.now():
                state = 'finished'
            s.state = state

    def unlink(self):
        for s in self:
            ag_ids = s.partner_id.hr_rfid_access_group_ids.filtered(
                lambda ag: ag.activate_on == s.start_date and ag.expiration == s.end_date
            )
            ag_ids.unlink()
        return super(BaseRFIDService, self).unlink()

    def extend_service(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("rfid_service_base.sale_wiz_action")
        action["name"] = _("Extend RFID Service for %s" % self.partner_id.name)
        action['binding_model_id'] = self.service_id
        action['view_id'] = self.env.ref("rfid_service_base.sale_wiz_action").id
        action["context"] = {
            'default_extend_sale_id': self.id,
            'default_service_id': self.service_id.id,
            'default_partner_id': self.partner_id.id,
            'default_card_number': self.card_number,
        }
        return action

    def partner_sales(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("rfid_service_base.hr_rfid_service_sale_action")
        action["name"]=_('Service Calendar for %s', self.partner_id.display_name)
        action["domain"]=[('partner_id', '=', self.partner_id.id)]
        return action

    def email_card(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_('Please fill the Customer e-mail'))
        return self.partner_id.action_send_badge_email()

    def print_card(self):
        self.ensure_one()
        return self.env.ref('hr_rfid.action_report_res_partner_foldable_badge').report_action(self.partner_id)

    def cancel_sale(self):
        for s in self.filtered(lambda sale: sale.state not in ['finished', 'canceled']):
            s.access_group_contact_rel.write({
                'activate_on': fields.Datetime.now() - timedelta(seconds=2),
                'expiration': fields.Datetime.now() - timedelta(seconds=1),
            })
            s.state = 'canceled'
            s.message_post(body=_('Manually canceled service'), message_type='comment')

    def process_event_data(self, user_event_id: HrRfidUserEvent):
        if self.service_id.activate_on_first_use and self.state == 'progress' and not self.activated_on:
            if user_event_id.reader_id.reader_types == '0':
                self.write({
                    'activated_on': user_event_id.event_time
                })
                self.access_group_contact_rel.write({
                    'activate_on': user_event_id.event_time,
                    'expiration': self.service_id.calc_end(start_date=user_event_id.event_time)
                })
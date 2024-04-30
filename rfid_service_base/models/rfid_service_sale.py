from datetime import timedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

import logging

from odoo.osv import expression

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

    @api.depends('access_group_contact_rel', 'access_group_contact_rel.state')
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
            elif (s.access_group_contact_rel.expiration - s.access_group_contact_rel.activate_on) == timedelta(
                    seconds=1):
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
        card_number = self.card_number or self.partner_id.hr_rfid_card_ids and self.partner_id.hr_rfid_card_ids[
            0].number
        action["context"] = {
            'default_extend_sale_id': self.id,
            'default_service_id': self.service_id.id,
            'default_partner_id': self.partner_id and self.partner_id.id or self.card_id.contact_id.id,
            'default_card_number': card_number or False,
        }
        return action

    def partner_sales(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("rfid_service_base.hr_rfid_service_sale_action")
        action["name"] = _('Service Calendar for %s', self.partner_id.display_name)
        action["domain"] = [('partner_id', '=', self.partner_id.id)]
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

    def fix_partner(self):
        for sale in self:
            if not sale.card_id and sale.partner_id:
                sale.card_id = sale.partner_id.hr_rfid_card_ids and sale.partner_id.hr_rfid_card_ids[0]
                sale.card_number = sale.card_id.number
                if sale.card_number == sale.card_id.name:
                    sale.card_id.card_reference = sale.name
            if sale.partner_id != sale.card_id.contact_id and sale.partner_id and sale.card_id.contact_id:
                if not sale.partner_id.hr_rfid_card_ids:
                    old_contact = sale.partner_id
                    sale.card_id.contact_id.write({
                        'name': sale.partner_id.name,
                        'email': sale.partner_id.email,
                        'mobile': sale.partner_id.mobile,
                    })
                    sale.card_id.card_reference = sale.partner_id.name
                    sale.partner_id = sale.card_id.contact_id
                    self.env['rfid.service.sale'].search([('partner_id', '=', old_contact.id)]).write(
                        {'partner_id': sale.partner_id.id})
                    old_contact.unlink()
            elif not sale.partner_id:
                sale.partner_id = sale.card_id.contact_id
            if not sale.access_group_contact_rel and sale.partner_id:
                agcr_id = sale.partner_id.hr_rfid_access_group_ids.filtered(
                    lambda
                        agcr: agcr.activate_on.date() == sale.start_date.date() or agcr.expiration.date() == sale.end_date.date()
                    # lambda agcr: agcr.expiration.date() == sale.end_date.date()
                )
                sale.access_group_contact_rel = agcr_id
            sale._compute_state()

        return True

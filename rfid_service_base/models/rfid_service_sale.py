from datetime import timedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service.sale'
    _description = 'RFID Service Sales'
    _order = 'create_date desc'
    _inherit = "mail.thread"

    _check_duplicates = models.Constraint(
        'unique (service_id, start_date, end_date, partner_id)',
        "Only one service for same period for given Customer!",
    )

    name = fields.Char(
        string='Sale Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('rfid.service'),
        help="""Unique identifier for this service sale transaction.
        
• Purpose: Track and reference individual service sales
• Generation: Automatically generated using system sequence
• Usage: Used in customer communications, reports, and internal tracking
• Format: Follows company's configured numbering sequence
        
This reference number identifies the specific sale in the system."""
    )
    service_id = fields.Many2one(
        comodel_name='rfid.service',
        string="Service",
        required=True,
        help="""RFID service that was sold to the customer.
        
• Purpose: Links this sale to the specific service offering
• Configuration: Inherits all service settings (duration, access rights, etc.)
• Pricing: Service determines access permissions and time limits
• Required: Every sale must be linked to a service
        
The service defines what access and duration the customer receives."""
    )
    start_date = fields.Datetime(
        string="Access Start Date",
        required=True,
        help="""Date and time when customer access begins.
        
• Activation: Customer's card becomes active at this date/time
• Scheduling: Can be set for future activation (advance bookings)
• Timezone: Interpreted according to user's timezone settings
• Calculation: Combined with service duration to determine end date
        
Customer will be able to access designated areas starting from this date/time."""
    )
    end_date = fields.Datetime(
        string="Access End Date",
        required=True,
        help="""Date and time when customer access expires.
        
• Expiration: Customer's card becomes inactive at this date/time
• Calculation: Usually computed from start date + service duration
• Manual override: Can be manually adjusted for custom service periods
• Security: Access is automatically revoked after this date/time
        
Customer will lose access to designated areas after this date/time."""
    )

    state = fields.Selection(
        selection=[
            ('registered', 'Registered'),
            ('progress', 'Active'),
            ('finished', 'Finished'),
            ('canceled', 'Canceled')
        ], 
        string="Status",
        compute='_compute_state',
        store=True,
        tracking=True,
        help="""Current status of this service sale.
        
• Registered: Sale created but service period hasn't started yet
• Active: Service is currently active and customer has access
• Finished: Service period has ended or all visits have been used
• Canceled: Service was manually canceled before completion
        
Status is automatically calculated based on dates, visits, and access permissions."""
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='service_id.company_id'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner', 
        string='Customer', 
        check_company=True, 
        index=True,
        domain=["&", ("is_company", "=", False), ("type", "=", "contact")],
        help="""Customer who purchased this service.
        
• Individual: Must be a person, not a company contact
• Creation: Can be created automatically during service sale process
• Communication: Used for sending emails and printing badges
• Tracking: Links all service sales to the same customer for history
        
This is the person who will receive access and communications about the service."""
    )
    card_id = fields.Many2one(
        comodel_name='hr.rfid.card', 
        string="RFID Card",
        check_company=True,
        help="""Physical or digital card assigned to the customer for access.
        
• Access method: Card that customer uses to gain physical access
• Card types: Can be RFID card, barcode card, or mobile badge
• Creation: Automatically created during service sale process
• Security: Activated/deactivated according to service period
        
This is the physical/digital token the customer uses to access areas."""
    )
    card_number = fields.Char(
        related='card_id.number',
        string="Card Number",
        help="Unique identifier/number of the card assigned to this service sale."
    )
    access_group_contact_rel = fields.Many2one(
        comodel_name='hr.rfid.access.group.contact.rel', 
        string="Access Permission",
        check_company=True,
        help="""Technical link between customer and access group that grants permissions.
        
• Purpose: System record that actually grants access to doors/areas
• Timing: Controls when access starts and ends
• Visits: Tracks remaining visits for visit-based services
• Automatic: Created and managed automatically by the system
        
This is the technical record that enables physical access for the customer."""
    )
    visits = fields.Integer(
        string='Remaining Visits',
        related='access_group_contact_rel.visits_counter',
        help="""Number of visits remaining for this service (for visit-based services).

• Purpose: Shows how many times customer can still access with this service
• Countdown: Automatically decreases each time customer uses their card
• Zero means: No more visits remaining (service access blocked)
• Unlimited: Visit-based services show actual count, time-based services may show 0

Only relevant for 'Visits based' and 'Time and Visits based' service types."""
    )

    # @api.depends('partner_id.hr_rfid_card_ids', 'partner_id.hr_rfid_access_group_ids')
    @api.depends('access_group_contact_rel', 'start_date', 'end_date')
    def _compute_state(self):
        for s in self:
            if not s.start_date:
                start_date = s.access_group_contact_rel.activate_on
                end_date = s.access_group_contact_rel.expiration
            else:
                start_date = s.start_date
                end_date = s.end_date
            state = 'registered'
            if (start_date <= fields.Datetime.now() <= end_date) and s.access_group_contact_rel.active_for_visits():
                state = 'progress'
            elif (s.access_group_contact_rel.expiration - s.access_group_contact_rel.activate_on) == timedelta(
                    seconds=1):
                state = 'canceled'
            elif (end_date <= fields.Datetime.now()) or not s.access_group_contact_rel.active_for_visits():
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

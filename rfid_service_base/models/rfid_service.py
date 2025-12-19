from random import randint

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service'
    _description = 'RFID Service'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    # _order = 'number'

    name = fields.Char(
        string="Service Name",
        help="""User-friendly name for this RFID service offering.
        
• Purpose: Identify the service for staff and customers
• Examples: "Daily Visitor Pass", "Monthly Gym Access", "Conference Badge"
• Usage: Displayed on service cards, reports, and customer communications
• Best practice: Use clear, descriptive names that explain the service purpose
        
This name appears throughout the system and on printed badges.""",
        required=True
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="""Whether this service is currently available for new sales.
        
• Active: Service can be sold and new customers can register
• Inactive: Service is archived and unavailable for new sales
• Existing sales: Continues to work for already registered customers
• Use case: Temporarily disable services or archive old offerings
        
Deactivate to stop new sales while preserving existing customer access."""
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    color = fields.Integer(
        string='Color',
        help="""Color coding for visual identification in kanban and other views.
        
• Visual organization: Helps distinguish different service types
• User interface: Used in kanban cards and service displays
• Customization: Choose colors that match your organization's branding
• Default: System assigns random colors if not specified
        
Colors improve visual organization when managing multiple services."""
    )
    displayed_image_id = fields.Many2one(
        'ir.attachment',
        domain="[('res_model', '=', 'rfid.service'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]",
        string='Cover Image',
        help="""Visual image displayed on service cards and promotional materials.
        
• Purpose: Visual identification and marketing appeal
• Display: Shown in kanban view, service cards, and customer portals
• Format: Supports common image formats (PNG, JPG, etc.)
• Branding: Use logos, photos, or graphics that represent the service
        
A good cover image helps customers quickly identify the service they need."""
    )
    tag_ids = fields.Many2many(
        comodel_name='rfid.service.tags',
        string='Service Tags',
        help="""Categorization tags for organizing and filtering services.
        
• Organization: Group related services together (e.g., 'VIP', 'Visitor', 'Staff')
• Filtering: Use in search panels and reports to find specific service types
• Color coding: Tags have colors for visual identification
• Multiple tags: Services can have multiple tags for flexible categorization
        
Use tags to create logical groupings that match your business needs."""
    )
    service_type = fields.Selection([
        ('time', 'Time based'),
        ('count', 'Visits based'),
        ('time_count', 'Time and Visits based'),
    ], 
    string="Service Type",
    default='time',
    help="""How this service controls customer access duration and usage.
    
• Time based: Access valid for a specific time period (days, weeks, months)
• Visits based: Access limited by number of entries (e.g., 5 visits)
• Time and Visits: Both time period AND visit count restrictions apply
    
Choose based on how you want to limit and charge for the service.""")
    visits = fields.Integer(
        string="Number of Visits",
        default=0,
        help="""Maximum number of times a customer can access with this service.
        
• Purpose: Limit usage for visit-based or combined service types
• Tracking: System automatically counts and decreases available visits
• Zero means: Unlimited visits (only for time-based services)
• Examples: 5 visits for "Weekly Gym Pass", 1 visit for "Single Day Access"
        
Only applies to 'Visits based' and 'Time and Visits based' service types."""
    )
    time_interval_number = fields.Integer(
        string="Duration Number",
        default=1,
        help="""Numeric part of the service duration (combined with Duration Unit).
        
• Purpose: Define how long the service access remains valid
• Examples: 7 days, 1 month, 2 weeks, 30 minutes
• Calculation: Combined with Duration Unit to create total service period
• Pricing: Longer durations typically have higher prices
        
Set to 1 for single-unit periods (1 day, 1 week, etc.)."""
    )
    time_interval_type = fields.Selection(
        [('minutes', 'Minutes'),
         ('hours', 'Hours'),
         ('days', 'Days'),
         ('weeks', 'Weeks'),
         ('months', 'Months')],
        string='Duration Unit',
        default='months',
        help="""Time unit for the service duration (combined with Duration Number).
        
• Minutes: Very short access (meeting rooms, temporary access)
• Hours: Short-term access (day passes, events)
• Days: Short-term services (daily visitor passes)
• Weeks: Medium-term access (weekly memberships)
• Months: Long-term services (monthly subscriptions)
        
Choose the unit that best matches your service offering period."""
    )
    time_interval_start = fields.Float(
        string="Access Start Time",
        help="""Daily start time when access is allowed (24-hour format).
        
• Format: Hours and minutes (e.g., 9.0 = 9:00 AM, 14.5 = 2:30 PM)
• Purpose: Restrict access to specific hours of the day
• 00:00 means: No time restriction (access allowed all day)
• Use cases: Office hours, gym hours, restricted access periods
        
Combine with Access End Time to create daily access windows.""",
        default=0
    )
    time_interval_end = fields.Float(
        string="Access End Time",
        help="""Daily end time when access is no longer allowed (24-hour format).
        
• Format: Hours and minutes (e.g., 17.0 = 5:00 PM, 23.5 = 11:30 PM)
• Purpose: Automatically restrict access after business hours
• 00:00 means: No time restriction (access allowed all day)
• Security: Prevents after-hours access even with valid cards
        
Must be later than Access Start Time to create a valid time window.""",
        default=0
    )
    access_group_id = fields.Many2one(
        comodel_name='hr.rfid.access.group',
        string="Access Group",
        required=True,
        help="""RFID access group that defines which doors customers can access.
        
• Purpose: Controls physical access permissions for service customers
• Door mapping: Determines which doors/areas this service provides access to
• Security: Customers only get access to doors included in this group
• Configuration: Must be set up before selling services
        
Choose the access group that matches the physical areas this service should provide."""
    )
    generate_barcode_card = fields.Boolean(
        string="Generate Barcode Cards",
        default=False,
        help="""Automatically create barcode-based cards instead of RFID cards.
        
• When enabled: System generates QR/barcode cards for mobile scanning
• When disabled: Traditional RFID cards are used
• Use cases: Mobile-first access, temporary visitors, events
• Card type: Automatically changes to barcode card type when enabled
        
Barcode cards can be scanned with mobile devices and don't require physical RFID cards."""
    )

    zone_id = fields.Many2one(
        comodel_name='hr.rfid.zone',
        string="Tracking Zone",
        help="""Optional zone for tracking customer presence and behavior.
        
• Purpose: Monitor when and how long customers stay in specific areas
• Analytics: Generate reports on zone usage and customer patterns
• Integration: Works with attendance and presence tracking systems
• Optional: Leave empty if zone tracking is not needed
        
Useful for understanding customer behavior and facility utilization."""
    )
    parent_id = fields.Many2one(
        comodel_name='res.partner',
        string="Parent Customer",
        help="""Parent company or organization that all service customers will be linked to.
        
• Purpose: Group individual customers under a parent organization
• Hierarchy: Creates customer hierarchy for reporting and management
• Billing: Useful for corporate accounts or group bookings
• Optional: Leave empty for individual customers without parent organization
        
Example: Link all conference attendees to the hosting company."""
    )
    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card Type',
        help="""Type of RFID card issued to customers for this service.
        
• Purpose: Defines the physical/technical card characteristics
• Compatibility: Must match your RFID readers and system setup
• Automatic: Changes to barcode type when 'Generate Barcode Cards' is enabled
• Default: Uses system default card type if not specified
        
Ensure the card type is compatible with your hardware and security requirements.""",
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        tracking=True,
    )
    fixed_time = fields.Boolean(
        string="Fixed Time Schedule",
        default=True,
        help="""Whether service times are fixed or can be customized per sale.
        
• Fixed (enabled): All sales use the same start/end times defined in service
• Flexible (disabled): Staff can customize start/end times for each individual sale
• Use cases: Fixed for standard services, flexible for custom bookings
• Control: Determines if operators can modify service timing during sales
        
Enable for standardized services, disable for custom or event-based access."""
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain=[("model", "=", "res.partner")],
        default=lambda self: self.env.ref('hr_rfid.card_barcode_mail_template_badge'),
        help="""Email template used when sending badges/cards to customers.
        
• Purpose: Customize the email content and appearance sent to customers
• Content: Can include card details, access instructions, and company branding
• Automation: Template is used when clicking 'Email Card' in sales process
• Default: Uses system default badge email template if not specified
        
Customize the template to match your organization's communication style.""",
    )
    print_template_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Print Template",
        domain=[("model", "=", "res.partner")],
        default=lambda self: self.env.ref('hr_rfid.action_report_res_partner_foldable_badge'),
        help="""Report template used when printing physical badges/cards for customers.
        
• Purpose: Define the layout and content of printed badges
• Customization: Can include logos, QR codes, access information, and design elements
• Usage: Template is used when clicking 'Print Card' in sales process
• Default: Uses system default foldable badge template if not specified
        
Customize to create professional badges that match your organization's branding."""
    )

    @api.onchange('generate_barcode_card')
    def _onchange_barcode(self):
        self.card_type = self.generate_barcode_card and self.env.ref(
            'hr_rfid.hr_rfid_card_type_barcode').id or self.env.ref('hr_rfid.hr_rfid_card_type_def').id

    def action_new_sale(self):
        ctx = {'default_service_id': self.id}
        if self.generate_barcode_card:
            hex_num, num = self.env['hr.rfid.card'].sudo().create_bc_card()
            ctx['default_card_number'] = num
        return {
            'name': _('New Sale - %s', self.name),
            'view_mode': 'form',
            'res_model': 'rfid.service.sale.wiz',
            'views': [(self.env.ref('rfid_service_base.sale_wiz_form').id, 'form')],
            'type': 'ir.actions.act_window',
            # 'res_id': wizard.id,
            'target': 'new',
            'context': ctx,
            # 'context': self.env.context,
        }

    def action_view_sales(self):
        result_action = self.env.ref('rfid_service_base.hr_rfid_service_sale_action').sudo().read()[0]
        result_action['domain'] = [('service_id', '=', self.id)]
        return result_action


class ServiceTags(models.Model):
    """ Tags of service's """
    _name = "rfid.service.tags"
    _description = "Service Tags"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(
        'Tag Name', 
        required=True,
        help="""Name of the service tag for categorization and filtering.
        
• Purpose: Create logical groupings of related services
• Examples: 'VIP', 'Visitor', 'Staff', 'Premium', 'Basic', 'Event'
• Usage: Used in search filters and service organization
• Uniqueness: Tag names must be unique across the system
        
Use clear, descriptive names that help organize your service offerings."""
    )
    color = fields.Integer(
        string='Color', 
        default=_get_default_color,
        help="""Color for visual identification of this tag in lists and kanban views.
        
• Visual organization: Helps quickly identify different tag categories
• User interface: Displayed in tag widgets and service cards
• Random default: System assigns random colors to new tags
• Customization: Choose colors that match your organization's color scheme
        
Colors improve visual organization when managing multiple service categories."""
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    _name_uniq = models.Constraint(
        'unique (name)',
        "Tag name already exists!",
    )

from odoo import fields, models, api


class Company(models.Model):
    _name = "res.company"
    _inherit = "res.company"
    _description = 'Company'

    realtime_refresh = fields.Boolean(
        string="Real-time View Refresh",
        help="""Enable automatic refresh of RFID views when hardware events occur.

• When enabled: Views automatically update when controllers, doors, webstacks, commands, alarms, or events change
• Live updates: Users see changes immediately without manual page refresh
• Performance: Uses browser notifications to update only when necessary
• Use cases: Control rooms, security monitoring, real-time dashboards

Note: Requires modern browser with WebSocket support. Disable if experiencing performance issues.""",
        default=False
    )

from odoo import fields, models


class Company(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    realtime_refresh = fields.Boolean(
        string="Real-time View Refresh",
        help="""Enable automatic refresh of views when data changes.

• When enabled: Views automatically update when records change
• Live updates: Users see changes immediately without manual page refresh
• Performance: Uses browser notifications to update only when necessary
• Use cases: Control rooms, monitoring, real-time dashboards

Note: Requires modern browser with WebSocket support.""",
        default=False
    )
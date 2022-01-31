from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = "hr.department"

    minimum_late_time = fields.Float(default=lambda s: 5/60)
    minimum_overtime = fields.Float(default=lambda s: 5/60)
    minimum_early_leave_time = fields.Float(default=lambda s: 5/60)

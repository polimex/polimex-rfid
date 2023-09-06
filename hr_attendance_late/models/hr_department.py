from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = "hr.department"

    ignore_early_come_time = fields.Float(
        help='Times smaller than this will be ignored in the calculations on a daily basis.', digits=(2, 2),
        default=lambda s: 10 / 60)
    ignore_late_time = fields.Float(
        help='Times smaller than this will be ignored in the calculations on a daily basis.', digits=(2, 2),
        default=lambda s: 5 / 60)
    ignore_early_leave_time = fields.Float(
        help='Times smaller than this will be ignored in the calculations on a daily basis.', digits=(2, 2),
        default=lambda s: 0 / 60)
    ignore_overtime = fields.Float(
        help='Times smaller than this will be ignored in the calculations on a daily basis.', digits=(2, 2),
        default=lambda s: 15 / 60)
    ignore_extra_time = fields.Float(
        help='Times smaller than this will be ignored in the calculations on a daily basis.', digits=(2, 2),
        default=lambda s: 10 / 60)

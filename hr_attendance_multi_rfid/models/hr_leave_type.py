from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    include_in_theoretical = fields.Boolean(
        string="Include in theoretical hours",
        help="If you check this mark, leaves in this category won't reduce "
             "the number of theoretical hours in the attendance report.",
    )

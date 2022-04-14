from odoo import fields, models, api


class HRRFIDVisitorManagement(models.Model):
    _name = 'hr.rfid.visitor.management'
    _description = 'Visitors management'

    name = fields.Char(string='Visitors plan', help='Visitors management plan name', required=True)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    color = fields.Integer(string='Color Index', help="Color")
    access_group_ids = fields.Many2many(
        comodel_name='hr.rfid.access.group',
        help='Access groups granted with this plan',
        required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain=[('is_company', '=', True)],
        string='Parent',
        help='Partner under who the visitor will create',
        required=True
    )
    end_to = fields.Float(
        string='Active to',
        help='The default deactivation time of visitor card',
        default=18,
        required=True

    )
    permitted_user_ids = fields.Many2many(
        comodel_name='res.users'
    )
    require_info = fields.Selection([
        ('none', 'Nothing'),
        ('name', 'Name Only'),
        ('name_visited', 'Name and visited person '),
        ('id_visited', 'Scan ID and fill visited person'),
    ],help='Operator need to enter information for the Visitor', default='none', required=True
    )
    notify_visited_employee = fields.Boolean(default=False)
    require_visited_employee_approval = fields.Boolean(
        default=False,
        help='Create activity for employee( if user connected)'
    )

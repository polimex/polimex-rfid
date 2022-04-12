from odoo import fields, models, api


class HRRFIDVisitorManagementVisit(models.Model):
    _name = 'hr.rfid.visitor.management.visit'
    _description = 'Visits'

    card = fields.Char(string='Card', help='Card number')
    plan = fields.Many2one(
        comodel_name='hr.rfid.visitor.management',
        required=True,
    )
    visited_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        domain={('is_company', '=', 'False')},
        string='Visited partners',
    )
    visited_employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Visited employees',
    )

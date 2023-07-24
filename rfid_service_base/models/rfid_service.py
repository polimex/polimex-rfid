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
        help='Friendly service name',
        required=True
    )
    active = fields.Boolean(
        default=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    color = fields.Integer(string='Color Index')
    displayed_image_id = fields.Many2one('ir.attachment',
                                         domain="[('res_model', '=', 'rfid.service'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]",
                                         string='Cover Image')
    tag_ids = fields.Many2many(
        comodel_name='rfid.service.tags',
        domain="[('company_id', '=', company_id)]",
        string='Tags')
    service_type = fields.Selection([
        ('time', 'Time based'),
        ('count', 'Visits based'),
        ('time_count', 'Time and Visits based'),
    ], default='time')
    visits = fields.Integer(
        default=0,
        help='Visits count'
    )
    time_interval_number = fields.Integer(
        default=1,
        help="Repeat every x.")
    time_interval_type = fields.Selection(
        [('minutes', 'Minutes'),
         ('hours', 'Hours'),
         ('days', 'Days'),
         ('weeks', 'Weeks'),
         ('months', 'Months')],
        string='Interval Unit',
        default='months'
    )
    time_interval_start = fields.Float(
        help='Service time to start. Format HH:MM. 00:00 means not use',
        default=0
    )
    time_interval_end = fields.Float(
        help='Service time to end. Format HH:MM. 00:00 means not use',
        default=0
    )
    access_group_id = fields.Many2one(
        comodel_name='hr.rfid.access.group',
        required=True,
    )
    generate_barcode_card = fields.Boolean(
        default=False,
        help='The card will be generated automatically for barcode reading'
    )

    zone_id = fields.Many2one(
        comodel_name='hr.rfid.zone'
    )
    parent_id = fields.Many2one(
        comodel_name='res.partner',
        help='All partners created from this service will be attached to this partner. It is optional.'
    )
    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Card type for registered cards from this service',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        tracking=True,
    )
    fixed_time = fields.Boolean(
        default=True,
        help='If the time is not fixed, the operator can change the start and end time of the service.'
    )

    @api.onchange('generate_barcode_card')
    def _onchange_barcode(self):
        self.card_type = self.generate_barcode_card and self.env.ref(
            'hr_rfid.hr_rfid_card_type_barcode').id or self.env.ref('hr_rfid.hr_rfid_card_type_def').id

    def action_new_sale(self):
        return {
            'name': _('New Sale - %s', self.name),
            'view_mode': 'form',
            'res_model': 'rfid.service.sale.wiz',
            'views': [(self.env.ref('rfid_service_base.sale_wiz_form').id, 'form')],
            'type': 'ir.actions.act_window',
            # 'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context,
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

    name = fields.Char('Name', required=True)
    color = fields.Integer(string='Color', default=_get_default_color)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]

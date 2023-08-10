from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service.sale'
    _description = 'RFID Service Sales'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('rfid.service'),
    )
    service_id = fields.Many2one(
        comodel_name='rfid.service',
        required=True
    )
    start_date = fields.Datetime(
        string="Service start",
        required=True
    )
    end_date = fields.Datetime(
        string="Service end",
        required=True
    )

    state = fields.Selection(
        selection=[
            ('registered', 'Registered'),
            ('progress', 'Progress'),
            ('finished', 'Finished')
        ], compute='_compute_state',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='service_id.company_id'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Customer', check_company=True, index=True,
        domain=["&", ("is_company", "=", False), ("type", "=", "contact")],
        # domain="[('company_id', '=', company_id)]",
        help="Linked partner to this service sale")
    card_id = fields.Many2one(
        comodel_name='hr.rfid.card', check_company=True,
        required=True
    )
    access_group_contact_rel = fields.Many2one(
        comodel_name='hr.rfid.access.group.contact.rel', check_company=True
    )

    @api.depends('partner_id.hr_rfid_card_ids', 'partner_id.hr_rfid_access_group_ids')
    def _compute_state(self):
        for s in self:
            if not s.start_date:
                acgcr = self.env['hr.rfid.access.group.contact.rel'].search([('contact_id', '=', s.partner_id.id)])
                start_date = acgcr and acgcr[0].activate_on
                end_date = acgcr and acgcr[0].expiration
            else:
                start_date = s.start_date
                end_date = s.end_date
            state = 'registered'
            if start_date <= fields.Datetime.now() <= end_date:
                state = 'progress'
            elif end_date <= fields.Datetime.now():
                state = 'finished'
            s.state = state
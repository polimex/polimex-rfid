# -*- coding: utf-8 -*-
from odoo import fields, models, _


class HrRfidOdooImportConflict(models.TransientModel):
    _name = 'hr.rfid.odoo.import.conflict'
    _description = 'RFID Odoo Import Conflict'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz',
        required=True,
        ondelete='cascade',
    )
    source_model = fields.Char(string='Model', readonly=True)
    source_id = fields.Integer(string='Source ID', readonly=True)
    source_name = fields.Char(string='Source Record', readonly=True)
    source_ref = fields.Char(string='Unique Key', readonly=True)
    target_id = fields.Integer(string='Target ID', readonly=True)
    target_name = fields.Char(string='Existing in Target', readonly=True)
    conflict_field = fields.Char(string='Conflict Field', readonly=True)
    resolution = fields.Selection([
        ('link', 'Link to existing'),
        ('create', 'Create new'),
        ('skip', 'Skip this record'),
    ], string='Resolution', default='link', required=True)


class HrRfidOdooImportLog(models.TransientModel):
    _name = 'hr.rfid.odoo.import.log'
    _description = 'RFID Odoo Import Log'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz',
        required=True,
        ondelete='cascade',
    )
    phase = fields.Char(string='Phase', readonly=True)
    model = fields.Char(string='Model', readonly=True)
    source_count = fields.Integer(string='Source Count', readonly=True)
    imported_count = fields.Integer(string='Imported', readonly=True)
    skipped_count = fields.Integer(string='Skipped', readonly=True)
    linked_count = fields.Integer(string='Linked', readonly=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', readonly=True)
    duration = fields.Float(string='Duration (s)', readonly=True)
    error_message = fields.Text(string='Error', readonly=True)


class HrRfidOdooImportCompanyLine(models.TransientModel):
    _name = 'hr.rfid.odoo.import.company.line'
    _description = 'RFID Odoo Import Company Mapping'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz',
        required=True,
        ondelete='cascade',
    )
    source_id = fields.Integer(string='Source Company ID', readonly=True)
    source_name = fields.Char(string='Source Company', readonly=True)
    do_import = fields.Boolean(string='Import', default=True)
    target_company_id = fields.Many2one(
        'res.company',
        string='Target Company',
    )

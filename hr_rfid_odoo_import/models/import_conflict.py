# -*- coding: utf-8 -*-
from odoo import fields, models, _


class HrRfidOdooImportConflict(models.TransientModel):
    _name = 'hr.rfid.odoo.import.conflict'
    _description = 'RFID Odoo Import Conflict'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz',
        required=True,
        ondelete='cascade',
        help="Parent import-run wizard this conflict belongs to.",
    )
    source_model = fields.Char(
        string='Model', readonly=True,
        help="Odoo model name of the conflicting record (e.g. hr.rfid.card, res.partner).",
    )
    source_id = fields.Integer(
        string='Source ID', readonly=True,
        help="Database ID of the record on the source instance.",
    )
    source_name = fields.Char(
        string='Source Record', readonly=True,
        help="Display name of the record on the source instance - shown so the operator can identify it.",
    )
    source_ref = fields.Char(
        string='Unique Key', readonly=True,
        help="The natural key that triggered the conflict (e.g. card number, EGN). Both sides match on this value.",
    )
    target_id = fields.Integer(
        string='Target ID', readonly=True,
        help="Database ID of the matching record on this (target) instance.",
    )
    target_name = fields.Char(
        string='Existing in Target', readonly=True,
        help="Display name of the existing target record - operator decides whether to keep it (Link) or create a new one (Create).",
    )
    conflict_field = fields.Char(
        string='Conflict Field', readonly=True,
        help="Field on which the two records collide (typically the unique constraint that fired).",
    )
    resolution = fields.Selection(
        [
            ('link', 'Link to existing'),
            ('create', 'Create new'),
            ('skip', 'Skip this record'),
        ],
        string='Resolution',
        help="What to do with this conflict during the import - Link: treat the existing record here as the same thing and re-use it. Create: bring the record over as a separate one. Skip: leave it out of the import. Left empty the import will not start, so nothing is merged behind your back.",
    )
    # Умишлено БЕЗ default и БЕЗ required: празната стойност е "операторът още не
    # е решил" и блокира прогона (виж `_compute_warnings` -> unresolved_conflicts).
    # Докато полето беше `required=True, default='link'`, конфликт не можеше да
    # остане неразрешен, блокиращата проверка беше мъртъв код, а всяко съвпадение
    # по текст се сливаше мълчаливо. На живо това закачи четците и вратите на
    # един клиент за контролера на друг (1 970 записа при чужд наемател).


class HrRfidOdooImportLog(models.TransientModel):
    _name = 'hr.rfid.odoo.import.log'
    _description = 'RFID Odoo Import Log'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz',
        required=True,
        ondelete='cascade',
        help="Parent import-run wizard this log entry belongs to.",
    )
    phase = fields.Char(
        string='Phase', readonly=True,
        help="Stage of the import pipeline (e.g. 'companies', 'access_groups', 'users', 'events'). Used to group log rows for the operator.",
    )
    model = fields.Char(
        string='Model', readonly=True,
        help="Odoo model processed during this phase.",
    )
    source_count = fields.Integer(
        string='Source Count', readonly=True,
        help="Number of records the source instance reported for this model+phase.",
    )
    imported_count = fields.Integer(
        string='Imported', readonly=True,
        help="Number of records actually created in the target during this phase.",
    )
    skipped_count = fields.Integer(
        string='Skipped', readonly=True,
        help="Number of records skipped (operator chose Skip in conflicts, or validation rejected them).",
    )
    rejected_count = fields.Integer(
        string='Rejected', readonly=True,
        help="Number of records the database refused because another record already holds the same unique value. Unlike Skipped, these were meant to come across - any figure above zero means data did not arrive and the run needs a look. A missing required value is a different case: it fails the whole step, which shows up as Error.",
    )
    linked_count = fields.Integer(
        string='Linked', readonly=True,
        help="Number of source records mapped to an existing target record instead of being created anew.",
    )
    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('skipped', 'Skipped'),
        ],
        string='Status', default='pending', readonly=True,
        help="Outcome of this phase - Pending: not yet started. Done: finished without error. Error: failed, see the Error column. Skipped: nothing to do here, either because the option was left unticked or because the source system does not have this kind of record at all.",
    )
    duration = fields.Float(
        string='Duration (s)', readonly=True,
        help="Wall-clock seconds this phase took. Useful to spot slow phases for the next run.",
    )
    error_message = fields.Text(
        string='Error', readonly=True,
        help="Error message captured if the phase status is Error - full traceback for debugging.",
    )


class HrRfidOdooImportCompanyLine(models.TransientModel):
    _name = 'hr.rfid.odoo.import.company.line'
    _description = 'RFID Odoo Import Company Mapping'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz',
        required=True,
        ondelete='cascade',
        help="Parent import-run wizard this company mapping belongs to.",
    )
    source_id = fields.Integer(
        string='Source Company ID', readonly=True,
        help="res.company ID on the source instance - the natural key used to match across instances.",
    )
    source_name = fields.Char(
        string='Source Company', readonly=True,
        help="Display name of the company on the source instance - shown for operator cross-check.",
    )
    do_import = fields.Boolean(
        string='Import', default=True,
        help="Untick to skip this source company entirely. Useful when you only want to migrate one tenant out of a multi-company source.",
    )
    target_company_id = fields.Many2one(
        'res.company',
        string='Target Company',
        help="Existing res.company on this instance to merge the source data into. Leave empty to create a fresh company with the source name.",
    )

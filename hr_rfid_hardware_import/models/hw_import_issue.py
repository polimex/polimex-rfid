from odoo import api, fields, models


class HwImportIssue(models.Model):
    _name = 'hr.rfid.hw.import.issue'
    _description = 'Hardware Survey Finding'
    _order = 'severity desc, id'

    run_id = fields.Many2one(
        'hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
        help="The survey this finding belongs to.")
    phase = fields.Selection([
        ('discovery', 'Network search'),
        ('read', 'Reading'),
        ('analysis', 'Analysis'),
        ('import', 'Import'),
    ], required=True, default='analysis', index=True,
        help="Which part of the survey raised the finding. The analysis rebuilds only its own "
             "findings; what the reading found stays until that module or controller is read again.")
    kind = fields.Selection([
        ('conflict_webstack', 'Module already registered'),
        ('conflict_ctrl', 'Controller already registered'),
        ('conflict_card', 'Card already registered'),
        ('ts_conflict', 'Schedules differ'),
        ('pin_conflict', 'PIN codes differ'),
        ('rights_union', 'Cards of one person differ'),
        ('anomaly', 'Unusual card record'),
        ('gap', 'Not supported by the controller'),
        ('decision', 'Decision taken'),
        ('report', 'Report line'),
        ('warning', 'Warning'),
    ], required=True, index=True,
        help="What kind of finding this is. Conflicts are about records that already "
             "exist here; the rest describe what was read.")
    severity = fields.Selection([
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('blocker', 'Must be resolved before the import'),
    ], required=True, default='info', index=True,
        help="Blockers stop the import until they are resolved; warnings and "
             "information only go into the report.")
    message = fields.Text(required=True, help="The finding, in plain words.")
    module_id = fields.Many2one('hr.rfid.hw.import.module', ondelete='cascade', index=True,
                                help="The module this finding is about, if any.")
    ctrl_id = fields.Many2one('hr.rfid.hw.import.ctrl', ondelete='cascade', index=True,
                              help="The controller this finding is about, if any.")
    card_id = fields.Many2one('hr.rfid.hw.import.card', ondelete='cascade', index=True,
                              help="The card this finding is about, if any.")
    person_id = fields.Many2one('hr.rfid.hw.import.person', ondelete='cascade', index=True,
                                help="The person this finding is about, if any.")
    slot_id = fields.Many2one('hr.rfid.hw.import.ts.slot', ondelete='cascade', index=True,
                              help="The schedule slot this finding is about, if any.")
    group_id = fields.Many2one('hr.rfid.hw.import.group', ondelete='cascade', index=True,
                               help="The proposed access group this finding is about, if any.")
    target_model = fields.Char(
        help="For conflicts: the kind of record that already exists here.")
    target_id = fields.Integer(
        help="For conflicts: the record that already exists here.")
    resolution = fields.Selection([
        ('none', 'Not decided'),
        ('link', 'Use the existing record'),
        ('skip', 'Leave this one out'),
        ('accept', 'Noted'),
    ], default='none', required=True,
        help="For a conflict: reuse the record already present, or leave the "
             "surveyed one out of the import. Nothing is merged without a decision.")
    resolved = fields.Boolean(
        compute='_compute_resolved', store=True,
        help="A blocker counts as resolved once a decision is recorded.")

    @api.depends('severity', 'resolution')
    def _compute_resolved(self):
        for issue in self:
            issue.resolved = issue.severity != 'blocker' or issue.resolution != 'none'

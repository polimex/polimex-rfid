from odoo import api, fields, models


class HwImportTs(models.Model):
    _name = 'hr.rfid.hw.import.ts'
    _description = 'Surveyed Time Schedule Slot'
    _order = 'ctrl_id, number'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey that read this slot.")
    ctrl_id = fields.Many2one('hr.rfid.hw.import.ctrl', required=True, ondelete='cascade', index=True,
                              help="The controller this slot was read from.")
    number = fields.Integer(string="Slot", required=True, help="Slot number on the controller (1-15).")
    raw_hex = fields.Char(string="Schedule (raw)", help="The slot content in the form the access control module stores schedules.")
    week_fingerprint = fields.Char(string="Weekly grid fingerprint", index=True, help="Fingerprint of the weekly grid, used to compare slots.")
    holiday_ref = fields.Integer(string="Holiday list", help="Holiday list the slot refers to.")
    is_empty = fields.Boolean(string="Empty", help="The slot holds no time periods at all.")
    summary = fields.Char(string="In words", help="The schedule in words, e.g. Mon-Fri 08:00-18:00.")
    slot_id = fields.Many2one('hr.rfid.hw.import.ts.slot', string="Slot across controllers", ondelete='set null', index=True,
                              help="The survey-wide slot this reading belongs to.")

    _ctrl_number_uniq = models.Constraint(
        'UNIQUE (ctrl_id, number)',
        'A controller holds each schedule slot once.')


class HwImportTsSlot(models.Model):
    _name = 'hr.rfid.hw.import.ts.slot'
    _description = 'Surveyed Schedule Slot (across controllers)'
    _order = 'number'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey this slot belongs to.")
    number = fields.Integer(string="Slot", required=True, help="Slot number (1-15), the same on every controller.")
    ts_ids = fields.One2many('hr.rfid.hw.import.ts', 'slot_id', string='Readings',
                             help="What each controller holds in this slot.")
    variant_count = fields.Integer(string="Different versions", compute='_compute_variants', store=True,
                                   help="How many different schedules the controllers hold in this slot.")
    used_by_rights = fields.Boolean(string="Used by card rights", help="At least one card right refers to this slot.")
    existing_ts_id = fields.Many2one('hr.rfid.time.schedule', string="This company's schedule", ondelete='set null',
                                     help="This company's schedule with the same number.")
    existing_is_empty = fields.Boolean(string="This company's is empty", help="This company's schedule with the same number is empty.")
    existing_differs = fields.Boolean(string="Differs from this company's", help="This company's schedule differs from what the controllers hold.")
    source_ctrl_id = fields.Many2one('hr.rfid.hw.import.ctrl', string="Take schedule from", ondelete='set null',
                                     help="The controller whose schedule is taken for this slot when the "
                                          "controllers disagree.")
    keep_existing = fields.Boolean(string="Keep this company's", help="Keep this company's schedule and do not take the controllers' one.")
    state = fields.Selection([
        ('ok', 'Consistent'),
        ('conflict', 'Controllers disagree'),
        ('resolved', 'Decided'),
    ], compute='_compute_state', store=True, index=True,
        help="Consistent: every controller holds the same schedule. Controllers disagree: pick "
             "the controller whose schedule to take. Decided: a choice was made.")
    decision_note = fields.Char(string="Note", help="What was decided for this slot and why.")
    summary = fields.Char(string="In words", compute='_compute_summary', help="The chosen schedule in words.")

    _run_number_uniq = models.Constraint(
        'UNIQUE (run_id, number)',
        'A survey holds each schedule slot once.')

    @api.depends('ts_ids.week_fingerprint', 'ts_ids.is_empty', 'ts_ids.ctrl_id.include')
    def _compute_variants(self):
        for slot in self:
            fingerprints = {ts.week_fingerprint for ts in slot.ts_ids
                            if not ts.is_empty and ts.ctrl_id.include}
            slot.variant_count = len(fingerprints)

    @api.depends('variant_count', 'source_ctrl_id', 'keep_existing')
    def _compute_state(self):
        for slot in self:
            if slot.variant_count <= 1:
                slot.state = 'ok'
            elif slot.source_ctrl_id or slot.keep_existing:
                slot.state = 'resolved'
            else:
                slot.state = 'conflict'

    @api.depends('ts_ids.summary', 'ts_ids.is_empty', 'ts_ids.ctrl_id.include', 'source_ctrl_id')
    def _compute_summary(self):
        for slot in self:
            chosen = slot._chosen_reading()
            slot.summary = chosen.summary if chosen else ''

    def _chosen_reading(self):
        """The controller reading this slot will be imported from, if any."""
        self.ensure_one()
        readings = self.ts_ids.filtered(lambda t: t.ctrl_id.include and not t.is_empty)
        if self.source_ctrl_id:
            readings = readings.filtered(lambda t: t.ctrl_id == self.source_ctrl_id)
        return readings[:1]

    def action_pick_source(self):
        """Take the schedule of the controller chosen in the list."""
        self.ensure_one()
        ctrl_id = self.env.context.get('source_ctrl_id')
        if ctrl_id:
            self.write({'source_ctrl_id': ctrl_id, 'keep_existing': False})
        return True

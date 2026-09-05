from odoo import api, fields, models

#: Lines older than this are removed by the daily vacuum; the survey rows keep
#: the raw replies themselves, so nothing the report needs is lost.
GC_DAYS = 90
GC_LIMIT = 5000


class HwImportCmdLog(models.Model):
    _name = 'hr.rfid.hw.import.cmd.log'
    _description = 'Hardware Survey Command Log'
    _order = 'id'

    run_id = fields.Many2one(
        'hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
        help="The survey during which this command was sent.")
    module_id = fields.Many2one(
        'hr.rfid.hw.import.module', ondelete='cascade', index=True,
        help="The module that relayed the command to its controllers.")
    address = fields.Integer(string="Controller address",
        help="Controller address on the module's bus the command was sent to.")
    opcode = fields.Char(string="Command",
        size=2, index=True,
        help="The command code. Only read commands are ever sent; the log proves it.")
    data_sent = fields.Char(string="Parameters",
        help="Parameters that went with the command (slot number, card page, ...).")
    e_code = fields.Integer(string="Reply code",
        help="Reply code: 0 means the controller answered normally; other values "
             "explain a retry or a gap in what could be read.")
    duration_ms = fields.Integer(string="Reply time (ms)", help="How long the module took to answer, in milliseconds.")
    response_hex = fields.Text(string="Reply (raw)", help="The raw reply, kept as evidence of what was read.")
    skewed = fields.Boolean(string="Reply for another command",
        help="The module answered for a different command; the reply was discarded "
             "and the command sent again.")
    attempt = fields.Integer(string="Attempt", help="Attempt number of this command (1 = first try).")
    note = fields.Char(string="Note", help="What the survey concluded from this reply, when relevant.")

    @api.autovacuum
    def _gc_cmd_logs(self):
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=GC_DAYS)
        records = self.search([('create_date', '<', cutoff)], limit=GC_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_LIMIT

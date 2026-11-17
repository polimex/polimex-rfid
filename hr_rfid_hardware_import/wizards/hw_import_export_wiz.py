from odoo import fields, models
from odoo.exceptions import UserError

from ..models.exporter import SurveyExporter


class HwImportExportWiz(models.TransientModel):
    _name = "hr.rfid.hw.import.export.wiz"
    _description = "Export what the survey read"

    run_id = fields.Many2one(
        "hr.rfid.hw.import.run",
        required=True,
        ondelete="cascade",
        help="The survey to export.",
    )
    file_format = fields.Selection(
        [
            ("xlsx", "Excel workbook (one sheet per kind of thing)"),
            ("json", "JSON (everything, raw replies included, for another system)"),
        ],
        required=True,
        default="xlsx",
        help="The workbook is for people: modules, controllers, schedules, cards, card records, access "
        "groups, people, findings and the raw replies, one sheet each. The JSON document holds the "
        "same and every decoded setting, for a program or a later import.",
    )
    include_commands = fields.Boolean(
        string="Include the command log",
        help="Every command sent to the hardware and its reply, as proof that only read commands were "
        "used. Long on a large site.",
    )

    def action_export(self):
        self.ensure_one()
        run = self.run_id
        if not run.read_at:
            raise UserError(
                self.env._("Nothing has been read yet; read the controllers first.")
            )
        exporter = SurveyExporter(run, include_commands=self.include_commands)
        if self.file_format == "json":
            raw, extension, mimetype = exporter.json_bytes(), "json", "application/json"
        else:
            raw, extension = exporter.xlsx_bytes(), "xlsx"
            mimetype = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "hardware-survey-%s.%s" % (run.id, extension),
                "type": "binary",
                "raw": raw,
                "mimetype": mimetype,
                "res_model": run._name,
                "res_id": run.id,
            }
        )
        run.message_post(
            body=self.env._("What the survey read was exported as a file."),
            attachment_ids=[attachment.id],
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

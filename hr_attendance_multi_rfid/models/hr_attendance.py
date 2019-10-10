from odoo import api, fields, models
from datetime import datetime, timedelta
import base64


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    theoretical_hours = fields.Float(
        compute="_compute_theoretical_hours", store=True, compute_sudo=True
    )

    hr_rfid_user_event_check_in_id = fields.Many2one("hr.rfid.event.user")
    hr_rfid_user_event_check_out_id = fields.Many2one("hr.rfid.event.user")

    @api.depends("check_in", "employee_id")
    def _compute_theoretical_hours(self):
        obj = self.env["hr.attendance.theoretical.time.report"]
        for record in self:
            record.theoretical_hours = obj._theoretical_hours(
                record.employee_id, record.check_in
            )

    @api.model
    def _check_for_forgotten_attendances(self):
        max_att = str(
            self.env["ir.config_parameter"].get_param(
                "hr_attendance_multi_rfid.max_attendance"
            )
        )
        max_att = max_att.split()

        if len(max_att) != 2:
            return

        if max_att[0][-1] == "h" and max_att[1][-1] == "m":
            h = max_att[0][:-1]
            m = max_att[1][:-1]
        elif max_att[0][-1] == "m" and max_att[1][-1] == "h":
            h = max_att[1][:-1]
            m = max_att[0][:-1]
        else:
            return

        td = timedelta(hours=int(h), minutes=int(m))

        atts = self.search([("check_out", "=", None)])

        for att in atts:
            check_out = att.check_in + td
            if check_out <= datetime.now():
                att.check_out = check_out


# ------------------------------------------------------------------------------------------------#
#                                                                                                #
#                                   EXPORT OPTIONS - ACC2OMZ, ENERSYS                            #
#                                                                                                #
# ------------------------------------------------------------------------------------------------#
class HrAttendanceExportWizard(models.TransientModel):
    _name = "hr.attendance.export.wizard"
    _description = "Exports attendances in two different formats - ACC2OMZ or Enersys"

    from_date = fields.Datetime(
        "From Date", default=lambda self: self._set_default_from()
    )
    to_date = fields.Datetime("To Date", default=lambda self: self._set_default_to())
    export_format = fields.Selection(
        selection=[("acc2omz", "Omeks2000 ACC2OMZ"), ("enersys", "Omeks2000 Enersys")],
        default="acc2omz",
        required=True,
    )
    state = fields.Selection([("choose", "choose"), ("get", "get")], default="choose")
    data = fields.Binary("File", readonly=True)
    name = fields.Char("FileName")
    no_content = fields.Char(
        "No content", help="Displays a message if there is no content."
    )
    period = fields.Selection(
        [("previous_month", "Previous month"), ("custom_date", "Custom date")],
        default="previous_month",
        required=True,
    )

    @api.model
    def _set_default_from(self):
        """
        Sets default start date in the date form.
        """
        today = datetime.today()
        previous = today - timedelta(days=1)

        day = 1
        month = previous.month if today.day == 1 else today.month
        year = previous.year if today.day == 1 and today.month == 1 else today.year
        return datetime(year, month, day)

    @api.model
    def _set_default_to(self):
        """
        Sets default end date in the date form.
        """
        today = datetime.today()
        previous = today - timedelta(days=1)

        day = today.day if today.day > 1 else previous.day
        month = previous.month if today.day == 1 else today.month
        year = previous.year if today.day == 1 and today.month == 1 else today.year
        return datetime(year, month, day)

    @api.multi
    def export_hr_attendances(self):
        """
        Exports attendances depending from the given from - to date, export format and separator.
        """

        def export_acc2omz(attendances, separator, encoding):
            """
            Retrurns the name of the file and its content, encoded.
            """
            filename = "ACC20MZ-{}.txt".format(datetime.now())
            filecontent = []

            for attendance in attendances:
                check_in = separator.join(
                    [
                        "{}1".format(attendance.id),
                        str(attendance.check_in.day),
                        str(attendance.check_in.month),
                        str(attendance.check_in.year),
                        str(attendance.check_in.hour),
                        str(attendance.check_in.minute),
                        str(attendance.check_in.second),
                        str(
                            attendance.hr_rfid_user_event_check_in_id.employee_id.barcode
                        ),
                        str(
                            attendance.hr_rfid_user_event_check_in_id.employee_id.identification_id
                        ),
                        "1",
                        "вход",
                        "----",
                    ]
                )
                filecontent.append(check_in)

                if attendance.check_out:
                    check_out = separator.join(
                        [
                            "{}2".format(attendance.id),
                            str(attendance.check_out.day),
                            str(attendance.check_out.month),
                            str(attendance.check_out.year),
                            str(attendance.check_out.hour),
                            str(attendance.check_out.minute),
                            str(attendance.check_out.second),
                            str(
                                attendance.hr_rfid_user_event_check_out_id.employee_id.barcode
                            ),
                            str(
                                attendance.hr_rfid_user_event_check_out_id.employee_id.identification_id
                            ),
                            "1",
                            "изход",
                            "----",
                        ]
                    )
                    filecontent.append(check_out)
            filecontent = base64.encodebytes(
                "\n".join(filecontent).encode(encoding)
            )
            return filename, filecontent

        def export_enersys(attendances, separator, encoding):
            """
            Retrurns the name of the file and its content, encoded.
            """
            filename = "ENERSYS-{}.txt".format(datetime.now())
            filecontent = []

            for attendance in attendances:

                check_in = separator.join(
                    [
                        "М: 001",
                        "ENTERANCE",
                        str(
                            attendance.hr_rfid_user_event_check_in_id.employee_id.barcode
                        ),
                        attendance.employee_id.display_name,
                        "вход",
                        datetime.strftime(attendance.check_in, "%d.%m.%y"),
                        datetime.strftime(attendance.check_in, " %H:%M"),
                    ]
                )

                filecontent.append(check_in)

                if attendance.check_out:
                    check_out = separator.join(
                        [
                            "М: 001",
                            "ENTERANCE",
                            str(
                                attendance.hr_rfid_user_event_check_in_id.employee_id.barcode
                            ),
                            attendance.employee_id.display_name,
                            "изход",
                            datetime.strftime(attendance.check_out, "%d.%m.%y"),
                            datetime.strftime(attendance.check_out, " %H:%M"),
                        ]
                    )
                    filecontent.append(check_out)

            filecontent = base64.encodebytes(
                "\n".join(filecontent).encode(encoding)
            )
            return filename, filecontent

        this = self[0]

        if this.period == "previous_month":
            today = datetime.today().replace(day=1)
            previous = today - timedelta(days=1)

            day = 1
            month = previous.month
            year = previous.year

            from_date = datetime(year, month, day)
            to_date = datetime(year, month, previous.day)
        else:
            from_date = this.from_date
            to_date = this.to_date

        separator = ","
        encoding = "windows-1251"
        export_format = this.export_format
        attendances = this.env["hr.attendance"].search(
            [("create_date", ">=", from_date), ("create_date", "<=", to_date)]
        )

        if export_format == "acc2omz":
            filename, filecontent = export_acc2omz(attendances, separator, encoding)
        elif export_format == "enersys":
            filename, filecontent = export_enersys(attendances, separator, encoding)

        if not filecontent:
            this.write(
                {
                    "no_content": "There are not any attendances for the given period {} - {}".format(
                        datetime.strftime(from_date, "%d.%m.%y"),
                        datetime.strftime(to_date, "%d.%m.%y"),
                    )
                }
            )

        this.write({"state": "get", "data": filecontent, "name": filename})
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.attendance.export.wizard",
            "view_mode": "form",
            "view_type": "form",
            "res_id": this.id,
            "views": [(False, "form")],
            "target": "new",
        }

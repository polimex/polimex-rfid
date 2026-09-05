import base64

from odoo import fields, models
from odoo.exceptions import UserError


class HwImportNamesWiz(models.TransientModel):
    _name = 'hr.rfid.hw.import.names.wiz'
    _description = 'Upload a names file'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade',
                             help="The survey the names are for.")
    file = fields.Binary(required=True, help="A CSV or Excel file with two columns: the name and the card number.")
    file_name = fields.Char(help="Name of the file.")

    def action_load(self):
        self.ensure_one()
        rows, columns_used = self._read_rows()
        if not rows:
            raise UserError(self.env._("The file has no usable lines. It needs two columns: a name and a card number."))
        from ..models.analyser import SurveyAnalyser
        counts = SurveyAnalyser(self.run_id).apply_names(rows)
        self.run_id.write({'names_file': self.file, 'names_file_name': self.file_name})
        message = self.env._(
            "%(matched)s lines matched a card, %(unmatched)s named a card no controller holds, "
            "%(duplicate)s repeated a number, %(invalid)s could not be read. %(merged)s names appear "
            "on more than one line and were merged into one person each - check them in the People tab.",
            **counts)
        name_col, number_col, width = columns_used
        if width > 2:
            message += ' ' + self.env._(
                "The file has %(width)s columns; column %(name)s was read as the name and column "
                "%(number)s as the card number.", width=width, name=name_col, number=number_col)
        self.run_id.message_post(body=message)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'type': 'info', 'title': self.env._('Names loaded'), 'message': message,
                       'sticky': True, 'next': {'type': 'ir.actions.act_window_close'}},
        }

    def _read_rows(self):
        """Rows of (line number, name, card number), read with the standard import reader."""
        raw = base64.b64decode(self.file)
        reader = self.env['base_import.import'].create({
            'res_model': 'hr.rfid.hw.import.name',
            'file': raw,
            'file_name': self.file_name or 'names.csv',
            'file_type': self._guess_type(),
        })
        try:
            _count, rows = reader._read_file({'quoting': '"', 'separator': '', 'encoding': '', 'sheet': ''})
        except Exception as exc:  # noqa: BLE001 - the reader raises many types; the operator needs one message
            raise UserError(self.env._("The file could not be read as CSV or Excel: %(error)s", error=exc)) from exc
        finally:
            reader.unlink()
        rows = [[str(cell or '').strip() for cell in row] for row in rows]
        rows = [row for row in rows if any(row)]
        if not rows:
            return [], (1, 2, 0)
        width = max(len(row) for row in rows)
        if width < 2:
            raise UserError(self.env._("The file has only one column; a name and a card number are needed."))
        number_col = self._number_column(rows, width)
        name_col = 0 if number_col != 0 else 1
        columns_used = (name_col + 1, number_col + 1, width)
        result = []
        for index, row in enumerate(rows, start=1):
            row = row + [''] * (width - len(row))
            number = row[number_col]
            name = row[name_col]
            if index == 1 and number and not any(ch.isdigit() for ch in number):
                continue  # a header line: text where a card number belongs
            result.append((index, name, number))
        return result, columns_used

    def _guess_type(self):
        name = (self.file_name or '').lower()
        if name.endswith('.xlsx'):
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        if name.endswith('.xls'):
            return 'application/vnd.ms-excel'
        if name.endswith('.ods'):
            return 'application/vnd.oasis.opendocument.spreadsheet'
        return 'text/csv'

    @staticmethod
    def _number_column(rows, width):
        """The column whose values are mostly digits is the card number column."""
        best, best_score = 1, -1
        for col in range(width):
            score = sum(1 for row in rows if col < len(row) and row[col] and
                        sum(ch.isdigit() for ch in row[col]) >= max(1, len(row[col]) * 0.8))
            if score > best_score:
                best, best_score = col, score
        return best

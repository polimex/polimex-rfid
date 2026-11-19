from odoo import api, fields, models

# The legend of form 76 is Cyrillic: a Latin letter that looks the same, typed
# on a Latin keyboard, prints alike but the sheet counts it in no column. The
# same letters the Bulgarian time-off catalog turns into Cyrillic in its own
# field (l10n_bg_hr_holidays, L10N_BG_FORM76_LATIN_TO_CYRILLIC), so a type
# shows one letter whichever field holds it.
LATIN_TO_CYRILLIC = str.maketrans("AaBCcEeHKMOoPpTXxy", "АаВСсЕеНКМОоРрТХху")
# The letter field of the Bulgarian time-off catalog, when it is installed;
# the sheet prints that one and falls back to this module's own when it is
# empty (reports/report_form_76_bg.py).
CATALOG_CODE = "l10n_bg_form76_code"


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    form76_code = fields.Char(
        "Код за форма 76",
        default="NA",
        help="Буквата, с която Форма 76 отбелязва дните на този отпуск, на кирилица: "
        "О - редовен отпуск, М - отпуск по майчинство, Б - отпуск по болест, "
        "Д - изпълнение на държавни задължения, А - с разрешение на администрацията. "
        "Дните се броят в колоната на буквата.",
    )
    form76_code_from_catalog = fields.Boolean(
        compute="_compute_form76_code_from_catalog",
        help="The Bulgarian time-off catalog holds this type's Form 76 letter, "
        "so the sheet prints that one.",
    )
    form76_law_reason = fields.Char(
        "Основание за оптуска",
        default="чл. 155, ал. 1 от Кодекса на труда /КТ/",
        help="Правното основание за този тип отпуск (член/алинея от КТ или друг нормативен акт). Излиза в съответната колона на справката.",
    )
    form76_description = fields.Text(
        "Описание",
        help="Свободен текст за вътрешни нужди — пояснява в кои ситуации да се ползва този тип отпуск. Не излиза в справката.",
    )

    @api.depends(lambda self: [CATALOG_CODE] if CATALOG_CODE in self._fields else [])
    def _compute_form76_code_from_catalog(self):
        has_catalog = CATALOG_CODE in self._fields
        for leave_type in self:
            leave_type.form76_code_from_catalog = bool(
                has_catalog and leave_type[CATALOG_CODE]
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._form76_code_in_cyrillic(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._form76_code_in_cyrillic(vals)
        return super().write(vals)

    @api.model
    def _form76_code_in_cyrillic(self, vals):
        """The Form 76 letter in ``vals`` with its Latin look-alikes made
        Cyrillic, as the legend of the sheet writes them."""
        if vals.get("form76_code"):
            vals["form76_code"] = vals["form76_code"].translate(LATIN_TO_CYRILLIC)

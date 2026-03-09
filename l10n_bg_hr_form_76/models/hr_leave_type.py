from odoo import fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    form76_code = fields.Char('Код за форма 76', default='NA')
    form76_law_reason = fields.Char('Основание за оптуска', default='чл. 155, ал. 1 от Кодекса на труда /КТ/')
    form76_description = fields.Text('Описание')

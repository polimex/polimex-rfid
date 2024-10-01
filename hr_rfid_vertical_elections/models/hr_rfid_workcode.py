# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
from odoo.api import ondelete


class HrRfidWorkcode(models.Model):
    _inherit = ['hr.rfid.workcode']

    user_action = fields.Selection(
        selection_add=[('yes', 'Vote Yes'), ('no', 'Vote No'), ('abstain', 'Vote Abstain')],
        ondelete={'yes': 'set default', 'no': 'set default', 'abstain': 'set default'},
    )


# -*- coding: utf-8 -*-
from odoo import models, api, fields
from datetime import datetime, timedelta


class HrRfidUserEvent(models.Model):
    _inherit = "hr.rfid.event.user"

    in_or_out = fields.Selection(
        selection=[ ('in', 'In'), ('out', 'Out'), ('no_info', 'No Info') ],
        help='Whether the user came in or out',
        string='User presence',
        default='no_info',
    )

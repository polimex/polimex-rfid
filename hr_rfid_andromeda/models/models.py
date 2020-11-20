# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Andromeda(models.Model):
    _name = 'hr_rfid_andromeda.hr_rfid_andromeda'

    name = fields.Char()
    ip_address = fields.Char()
    database = fields.Char()

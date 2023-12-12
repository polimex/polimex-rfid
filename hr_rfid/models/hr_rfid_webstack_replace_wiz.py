# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _, SUPERUSER_ID, tools

import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrRfidWebstackReplaceWiz(models.TransientModel):
    _name = 'hr.rfid.webstack.replace.wiz'
    _description = 'Wizard for replacing one webstack with another'

    source_webstack_id = fields.Many2one(
        comodel_name='hr.rfid.webstack',
        context={'active_test': False},
    )
    destination_webstack_id = fields.Many2one(
        comodel_name='hr.rfid.webstack',
        context={'active_test': False},
    )
    source_controller_ids = fields.One2many(
        'hr.rfid.ctrl',
        'webstack_id',
        related='source_webstack_id.controllers'
    )
    destination_controller_ids = fields.One2many(
        'hr.rfid.ctrl',
        'webstack_id',
        related='destination_webstack_id.controllers'
    )
    replace_existing = fields.Boolean(
        help="Replace existing controllers in destination module"
    )

    @api.onchange('destination_webstack_id')
    def _onchange_destination_webstack_id(self):
        if self.destination_webstack_id:
            return {'domain': {'source_webstack_id': [('id', '!=', self.destination_webstack_id.id)]}}
        else:
            return {'domain': {'source_webstack_id': []}}

    @api.onchange('source_webstack_id')
    def _onchange_source_webstack_id(self):
        if self.source_webstack_id:
            return {'domain': {'destination_webstack_id': [('id', '!=', self.source_webstack_id.id)]}}
        else:
            return {'domain': {'destination_webstack_id': []}}

    def confirm_transfer(self):
        if not self.source_webstack_id or not self.destination_webstack_id:
            raise ValidationError(_('Please select source and destination Module'))
        if self.source_webstack_id == self.destination_webstack_id:
            raise ValidationError(_('Use different modules for this operation!'))
        if self.replace_existing:
            self.destination_webstack_id.controllers.unlink()
        self.source_webstack_id.controllers.webstack_id = self.destination_webstack_id.id
        self.source_webstack_id.active = False
        self.destination_webstack_id.active = True
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        link = f"{base_url}/web#id={self.destination_webstack_id.id}&model=hr.rfid.webstack&view_type=form"
        message = _("Controllers moved to <a href='%s'>Module %s</a>", link, self.destination_webstack_id.display_name)
        self.source_webstack_id.message_post(body=message, message_type='comment')

        link = f"{base_url}/web#id={self.source_webstack_id.id}&model=hr.rfid.webstack&view_type=form"
        message = _("Controllers moved from <a href='%s'>Module %s</a>", link, self.source_webstack_id.display_name)
        self.destination_webstack_id.message_post(body=message, message_type='comment')

        pass

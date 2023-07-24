# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import timedelta, datetime
from enum import Enum
import secrets
import logging

from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

RFID_CARD_READABLE_FIELDS = {
    'id',
    'active',
    'name',
    'number',
    'card_reference',
    'card_type',
    'employee_id',
    'contact_id',
    'activate_on',
    'deactivate_on',
    'cloud_card',
    'create_date',
    'write_date',
    'company_id',
    'display_name',
}

RFID_CARD_WRITABLE_FIELDS = {
    'active',
}

class HrRfidCard(models.Model):
    _name = 'hr.rfid.card'
    _description = 'Card'
    _inherit = ['hr.rfid.card', 'portal.mixin']

    @property
    def SELF_READABLE_FIELDS(self):
        return RFID_CARD_READABLE_FIELDS | self.SELF_WRITABLE_FIELDS

    @property
    def SELF_WRITABLE_FIELDS(self):
        return RFID_CARD_WRITABLE_FIELDS

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields = super().fields_get(allfields=allfields, attributes=attributes)
        if not self.env.user.has_group('base.group_portal'):
            return fields
        readable_fields = self.SELF_READABLE_FIELDS
        public_fields = {field_name: description for field_name, description in fields.items() if field_name in readable_fields}

        writable_fields = self.SELF_WRITABLE_FIELDS
        for field_name, description in public_fields.items():
            if field_name not in writable_fields and not description.get('readonly', False):
                # If the field is not in Writable fields and it is not readonly then we force the readonly to True
                description['readonly'] = True

        return public_fields

    def _compute_access_url(self):
        super(HrRfidCard, self)._compute_access_url()
        for card in self:
            card.access_url = '/my/webcard/%s' % card.id

    def _compute_access_warning(self):
        super(HrRfidCard, self)._compute_access_warning()
        for card in self.filtered(lambda x: x.card_type != self.env.ref('hr_rfid.hr_rfid_card_type_barcode')):
            card.access_warning = _(
                "The card cannot be shared with the recipient(s) because the type is not Barcode.")

    def _ensure_fields_are_accessible(self, fields, operation='read', check_group_user=True):
        """" ensure all fields are accessible by the current user

            This method checks if the portal user can access to all fields given in parameter.
            By default, it checks if the current user is a portal user and then checks if all fields are accessible for this user.

            :param fields: list of fields to check if the current user can access.
            :param operation: contains either 'read' to check readable fields or 'write' to check writable fields.
            :param check_group_user: contains boolean value.
                - True, if the method has to check if the current user is a portal one.
                - False if we are sure the user is a portal user,
        """
        assert operation in ('read', 'write'), 'Invalid operation'
        if fields and (not check_group_user or self.env.user.has_group('base.group_portal')) and not self.env.su:
            unauthorized_fields = set(fields) - (self.SELF_READABLE_FIELDS if operation == 'read' else self.SELF_WRITABLE_FIELDS)
            if unauthorized_fields:
                raise AccessError(_('You cannot %s %s fields in card.', operation if operation == 'read' else '%s on' % operation, ', '.join(unauthorized_fields)))

    def read(self, fields=None, load='_classic_read'):
        self._ensure_fields_are_accessible(fields)
        return super(HrRfidCard, self).read(fields=fields, load=load)

    def mapped(self, func):
        # Note: This will protect the filtered method too
        if func and isinstance(func, str):
            fields_list = func.split('.')
            self._ensure_fields_are_accessible(fields_list)
        return super(HrRfidCard, self).mapped(func)

    @api.model
    def _ensure_portal_user_can_write(self, fields):
        for field in fields:
            if field not in self.SELF_WRITABLE_FIELDS:
                raise AccessError(_('You have not write access of %s field.') % field)

    @api.model_create_multi
    def create(self, vals_list):
        is_portal_user = self.env.user.has_group('base.group_portal')
        if is_portal_user:
            self.check_access_rights('create')
        for vals in vals_list:
            if is_portal_user:
                self._ensure_fields_are_accessible(vals.keys(), operation='write', check_group_user=False)
        # The sudo is required for a portal user as the record creation
        # requires the read access on other models, as mail.template
        # in order to compute the field tracking
        was_in_sudo = self.env.su
        if is_portal_user:
            ctx = {
                key: value for key, value in self.env.context.items()
                if key == 'default_project_id' \
                   or not key.startswith('default_') \
                   or key[8:] in self.SELF_WRITABLE_FIELDS
            }
            self = self.with_context(ctx).sudo()
        cards = super(HrRfidCard, self).create(vals_list)
        return cards

    def preview_card(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }
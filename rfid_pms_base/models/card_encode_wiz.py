from datetime import datetime, timedelta, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RfidPmsBaseCardEncodeWiz(models.TransientModel):
    _name = 'rfid_pms_base.card_encode_wiz'
    _description = 'Base PMS Card encoding Wizard'

    def _compute_mode(self):
        if self.env.context.get('current', False):
            return 'current'
        if self.env.context.get('new', False):
            return 'new'
        # Wizard is reachable only from the kanban "New" / "Add" buttons,
        # both of which set one of those context flags. A direct open with
        # no context is a misconfiguration.
        raise UserError(_(
            "This wizard must be opened from a room's "
            "kanban card (use the New or Add button)."
        ))

    def _get_room_id(self):
        return self.env['rfid_pms_base.room'].browse(
            self.env.context.get("active_id", [])
        )

    def _get_reservation_seq(self):
        if self.env.context.get('new', False):
            return self.env['ir.sequence'].next_by_code('base.pms.reservation')

    def _default_checkin(self):
        mode = self._compute_mode()
        if mode == 'new':
            return fields.Datetime.now()
        if mode == 'current' and self._get_room_id().all_contact_ids[:1]:
            first_contact = self._get_room_id().all_contact_ids[0].contact_id
            if first_contact.hr_rfid_card_ids:
                return first_contact.hr_rfid_card_ids[0].activate_on
        return fields.Datetime.now()

    def _default_checkout(self):
        mode = self._compute_mode()
        default = datetime.combine(fields.Date.today() + timedelta(days=1), time(hour=9))
        if mode == 'current' and self._get_room_id().all_contact_ids[:1]:
            first_contact = self._get_room_id().all_contact_ids[0].contact_id
            if first_contact.hr_rfid_card_ids:
                return first_contact.hr_rfid_card_ids[0].deactivate_on
        return default

    room_id = fields.Many2one(comodel_name='rfid_pms_base.room', default=_get_room_id)
    reservation = fields.Char(default=_get_reservation_seq)
    checkin_date = fields.Datetime(string="Check In", default=_default_checkin)
    checkout_date = fields.Datetime(string="Check Out", default=_default_checkout)
    mode = fields.Selection(selection=[
        ('new', 'New Reservation'),
        ('current', 'Current Reservation'),
    ], default=_compute_mode)

    card_number = fields.Char(string='The card number', size=10, required=True)

    def write_card(self):
        if (self.checkout_date - self.checkin_date) < timedelta(seconds=1):
            raise UserError(_('Wrong validity interval'))
        if not self.room_id:
            raise UserError(_('Please select a room'))
        if not self.card_number:
            raise UserError(_('Please scan a card'))
        if (self.checkout_date - self.checkin_date) > timedelta(days=30):
            raise UserError(_('The period for this card is more than 30 days'))

        card_number = self.card_number.zfill(10)
        existing_card = self.env['hr.rfid.card'].with_context(active_test=False).search(
            [('number', '=', card_number)]
        )
        if existing_card:
            if (not existing_card.active) or existing_card.contact_id:
                existing_card.unlink()
            else:
                raise UserError(_('Card already in use for {}').format(existing_card.employee_id.name))

        count = len(self.room_id.all_contact_ids)
        if not self.reservation:
            if count > 0:
                parent = self.room_id.all_contact_ids[0].contact_id.parent_id
            else:
                parent = self.env['res.partner'].create({"name": self._get_reservation_seq()})
        else:
            parent = self.env['res.partner'].create({"name": self.reservation})
            count = 0
            if self.room_id.all_contact_ids:
                self.room_id.all_contact_ids.contact_id.hr_rfid_card_ids.unlink()
                self.room_id.all_contact_ids.contact_id.hr_rfid_access_group_ids.unlink()

        self.env['res.partner'].create({
            "name": _("Guest {n} for ").format(n=count + 1) + parent.name,
            "parent_id": parent.id,
            'hr_rfid_card_ids': [(0, 0, {
                'number': card_number,
                'activate_on': self.checkin_date,
                'deactivate_on': self.checkout_date,
            })],
            'hr_rfid_access_group_ids': [(0, 0, {
                'access_group_id': self.room_id.access_group_id.id,
                'expiration': self.checkout_date,
            })],
        })

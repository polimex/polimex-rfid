# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, http


class HrRfidZone(models.Model):
    _name = 'hr.rfid.zone'
    _description = 'Zone'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Zone Name',
        track_visibility='onchange',
        required=True,
    )

    anti_pass_back = fields.Boolean(
        string='Anti-Pass Back',
        help="Disallow people in the zone to enter again, or leave if they're not in it",
    )

    log_out_on_exit = fields.Boolean(
        string='Logout on Exit',
        help='Whether to log people out on exit',
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        'hr_rfid_zone_door_rel',
        'zone_id',
        'door_id',
        string='Doors',
        help='Doors in this zone',
        track_visibility='onchange',
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Employees currently in this zone',
    )

    contact_ids = fields.Many2many(
        'res.partner',
        string='Contacts',
        help='Contacts currently in this zone',
    )

    def person_went_through(self, event):
        person = event.employee_id or event.contact_id

        if not person:
            return

        is_employee = isinstance(person, type(self.env['hr.employee']))

        for zone in self:
            person_left = (is_employee and person in zone.employee_ids) \
                          or (not is_employee and person in zone.contact_ids)
            if person_left:
                zone.person_left(person, event)
            else:
                zone.person_entered(person, event)

    def person_entered(self, person, event):
        is_employee = isinstance(person, type(self.env['hr.employee']))

        for zone in self:
            if (is_employee and person in zone.employee_ids) \
                    or (not is_employee and person in zone.contact_ids):
                continue

            if zone.anti_pass_back:
                HrRfidZone._create_person_entered_cmd(zone, person, event)

            if is_employee:
                zone.employee_ids = zone.employee_ids + person
            else:
                zone.contact_ids = zone.contact_ids + person

    def person_left(self, person, event):
        is_employee = isinstance(person, type(self.env['hr.employee']))

        for zone in self:
            if (is_employee and person not in zone.employee_ids) \
                    or (not is_employee and person not in zone.contact_ids):
                continue

            if zone.anti_pass_back or len(zone.door_ids.filtered("apb_mode")) > 0:
                HrRfidZone._create_person_left_cmd(zone, person, event)

            if zone.log_out_on_exit:
                HrRfidZone._log_person_out(zone, person)

            if is_employee:
                zone.employee_ids = zone.employee_ids - person
            else:
                zone.contact_ids = zone.contact_ids - person

    def clear_employees(self):
        for zone in self:
            for emp in zone.employee_ids:
                zone.person_left(emp, self.env['hr.rfid.event.user'])
            zone.employee_ids = self.env['hr.employee']

    def clear_contacts(self):
        for zone in self:
            for cont in zone.contact_ids:
                zone.person_left(cont, self.env['hr.rfid.event.user'])
            zone.contact_ids = self.env['res.partner']

    def _create_person_entered_cmd(self, person, event):
        self._change_apb_cmd(person, event, True)

    def _create_person_left_cmd(self, person, event):
        self._change_apb_cmd(person, event, False)

    def _change_apb_cmd(self, person, event, enable_exiting=True):
        cmd_env = self.env['hr.rfid.command']
        for zone in self:
            doors = zone.door_ids - event.door_id
            for door in doors:
                if not door.apb_mode:
                    continue
                for card in person.hr_rfid_card_ids:
                    cmd_env.change_apb_flag(door, card, enable_exiting)

    def _log_person_out(self, person):
        session_storage = http.root.session_store
        sids = session_storage.list()
        person.log_person_out(sids)


class HrRfidZoneDoorsWizard(models.TransientModel):
    _name = 'hr.rfid.zone.doors.wiz'
    _description = 'Add or remove doors to the zone'

    def _default_zone(self):
        return self.env['hr.rfid.zone'].browse(self._context.get('active_ids'))

    zone_id = fields.Many2one(
        'hr.rfid.zone',
        string='Zone',
        required=True,
        default=_default_zone,
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        string='Doors',
        help='Which doors to add to the access group',
        required=True,
    )

    def add_doors(self):
        self.ensure_one()
        self.zone_id.door_ids = self.zone_id.door_ids + self.door_ids

    def remove_doors(self):
        self.ensure_one()
        self.zone_id.door_ids = self.zone_id.door_ids - self.door_ids

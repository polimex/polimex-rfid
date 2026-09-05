import json

from odoo import api, fields, models


class HwImportPerson(models.Model):
    _name = 'hr.rfid.hw.import.person'
    _description = 'Surveyed Card Holder'
    _order = 'source, name'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey this person belongs to.")
    name = fields.Char(required=True, help="Name as it will be created here.")
    name_key = fields.Char(string="Name (normalised)", index=True, help="The name normalised for matching (spaces and case).")
    source = fields.Selection([
        ('file', 'From the names file'),
        ('placeholder', 'Generated'),
    ], required=True, default='placeholder', index=True,
        help="From the names file: the name came from the uploaded list. Generated: no name "
             "was known for the card, so a placeholder was made up from the card number.")
    owner_type = fields.Selection(string="Create as", selection=[
        ('contact', 'Contact'),
        ('employee', 'Employee'),
    ], required=True, default='contact',
        help="Create this person as a contact or as an employee. Employees need a department.")
    card_ids = fields.One2many('hr.rfid.hw.import.card', 'person_id', string='Cards',
                               help="The cards this person will own.")
    card_count = fields.Integer(string="Number of cards", compute='_compute_review', store=True, help="How many cards this person has.")
    pin = fields.Char(string="PIN", size=4, help="PIN code taken from the cards, when they agree on one.")
    pin_conflict = fields.Boolean(string="PIN codes differ", compute='_compute_review', store=True,
                                  help="The person's cards carry different PIN codes; none is imported.")
    rights_differ = fields.Boolean(string="Cards open different doors", compute='_compute_review', store=True,
                                   help="The person's cards open different doors today. After the import every "
                                        "card of a person opens the same doors: the union of what they open now.")
    ts_conflict = fields.Boolean(string="Same door, different schedules", compute='_compute_review', store=True,
                                 help="Two cards of this person open the same door on different schedules; "
                                      "this system cannot hold that, so the person must be split.")
    review_state = fields.Selection(string="Review", selection=[
        ('ok', 'Ready'),
        ('review', 'Please check'),
        ('blocked', 'Must be resolved'),
    ], compute='_compute_review', store=True, index=True,
        help="Please check: the person was merged from several lines or the cards differ. "
             "Must be resolved: the cards cannot coexist on one person.")
    include = fields.Boolean(default=True, help="Create this person and their cards during the import.")
    employee_id = fields.Many2one('hr.employee', string="Employee here", ondelete='set null',
                                  help="The employee created or reused by the import.")
    partner_id = fields.Many2one('res.partner', string="Contact here", ondelete='set null',
                                 help="The contact created or reused by the import.")
    merged = fields.Boolean(help="Several lines of the names file were merged into this person.")
    name_line_ids = fields.One2many('hr.rfid.hw.import.name', 'person_id', string='Names file lines',
                                    help="The lines of the names file that name this person.")

    @api.depends('card_ids', 'card_ids.rights_key', 'card_ids.pin', 'card_ids.door_rights_json', 'merged')
    def _compute_review(self):
        for person in self:
            cards = person.card_ids
            person.card_count = len(cards)
            pins = {c.pin for c in cards if c.pin}
            person.pin_conflict = len(pins) > 1
            keys = {c.rights_key for c in cards}
            person.rights_differ = len(cards) > 1 and len(keys) > 1
            seen = {}
            ts_conflict = False
            for card in cards:
                # Written by the analysis; a value that does not parse must
                # surface, not turn a blocked person into an accepted one.
                rights = json.loads(card.door_rights_json or '[]')
                for right in rights:
                    key = (right.get('ctrl'), right.get('door'))
                    if key in seen and seen[key] != right.get('ts'):
                        ts_conflict = True
                    seen.setdefault(key, right.get('ts'))
            person.ts_conflict = ts_conflict
            if ts_conflict:
                person.review_state = 'blocked'
            elif person.merged or person.rights_differ or person.pin_conflict:
                person.review_state = 'review'
            else:
                person.review_state = 'ok'

    def action_split(self):
        """One person per card; the names-file lines follow their card."""
        for person in self:
            if len(person.card_ids) < 2:
                continue
            for card in person.card_ids[1:]:
                twin = person.copy({'name': person.name, 'card_ids': False, 'merged': False})
                card.person_id = twin
                person.name_line_ids.filtered(lambda line: line.card_id == card).write({'person_id': twin.id})
            person.merged = False
        return True

    def action_merge_into(self, other):
        """Move every card of ``other`` to this person."""
        self.ensure_one()
        twins = other - self
        for twin in twins:
            twin.card_ids.write({'person_id': self.id})
            twin.name_line_ids.write({'person_id': self.id})
            twin.unlink()
        if twins:
            # Only a merge that moved something marks the person for review.
            self.merged = True
        return True

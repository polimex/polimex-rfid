from odoo import fields, models, api


class BalanceHistory(models.Model):
    _name = 'hr.rfid.vending.balance.history'
    _description = 'Balance history for employees'
    _order = 'id desc'

    name = fields.Char(
        string='Person Responsible/Item',
        compute='_compute_name',
    )

    person_responsible = fields.Many2one(
        'res.users',
        string='Person responsible for the change',
        default=lambda self: self.env.uid,
        readonly=True,
    )

    balance_change = fields.Float(
        string='Balance change',
        help="How much was deposited/withdrawn from the employee's balance",
        required=True,
        readonly=True,
    )

    balance_result = fields.Float(
        string='Balance result',
        help='How much the balance was after the change',
        required=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        readonly=True,
    )
    department_id = fields.Many2one(
        'hr.department', 'Department',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        related='employee_id.department_id',
        store=True
    )


    vending_event_id = fields.Many2one(
        'hr.rfid.vending.event',
        string='Event',
        ondelete='set null',
        readonly=True,
    )

    auto_refill_id = fields.Many2one(
        'hr.rfid.vending.auto.refill',
        string='Auto Refill Event',
        ondelete='set null',
        readonly=True,
    )

    item_id = fields.Many2one(
        'product.template',
        string='Item Sold',
        compute='_compute_item_sold',
        store=True,
        ondelete='set null',
    )

    def _compute_name(self):
        for it in self:
            if len(it.vending_event_id) > 0 and len(it.vending_event_id.item_sold_id) > 0:
                it.name = it.vending_event_id.item_sold_id.name
            else:
                it.name = it.person_responsible.name

    def _compute_item_sold(self):
        for it in self:
            it.item_id = it.vending_event_id.item_sold_id

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta, datetime, time
from decimal import Decimal


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    hr_rfid_vending_balance = fields.Float(
        string='Vending Balance',
        help="""Company-provided balance for vending machine purchases.
        
• Purpose: Budget allocated by employer for employee refreshments
• Usage: Automatically deducted when purchasing items from vending machines
• Refills: Can be topped up manually or automatically via monthly refill settings
• Limits: Combined with personal balance and daily limits for spending control
        
This balance represents company funds available to the employee for vending purchases.""",
        default=0.0,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_recharge_balance = fields.Float(
        string='Self Recharge Balance',
        help="""Personal balance loaded by the employee using their own money.
        
• Source: Employee's personal funds added to their vending account
• Independence: Separate from company-provided vending balance
• Usage: Combined with company balance for total available spending power
• Control: Employee manages this balance independently
        
This represents the employee's personal money available for vending purchases.""",
        default=0.0,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_negative_balance = fields.Boolean(
        string='Allow Negative Balance',
        help="""Allow employee to spend more than their current balance (credit system).
        
• When enabled: Employee can make purchases even with insufficient balance
• Credit limit: Set maximum debt amount in the 'Limit' field below
• Use cases: Trust-based system, salary deduction arrangements
• When disabled: Purchases blocked when balance reaches zero
        
Useful for employees with payment arrangements or trusted staff members.""",
        tracking=True,
        groups="hr_rfid_vending.group_customer",
    )

    # Only displayed if negative_balance is true
    hr_rfid_vending_limit = fields.Float(
        string='Credit Limit',
        help="""Maximum debt amount when negative balance is allowed.
        
• Purpose: Set maximum amount employee can owe when using credit system
• Example: If set to 50, employee can spend up to 50 units below zero balance
• Control: Prevents unlimited debt accumulation
• Only active: When 'Allow Negative Balance' is enabled above
        
Set to 0 for unlimited credit (not recommended).""",
        default=0.0,
        tracking=True,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_in_attendance = fields.Boolean(
        string='Require Active Attendance',
        help="""Restrict vending purchases to work hours only.
        
• When enabled: Employee can only buy items while checked in for attendance
• When disabled: Purchases allowed regardless of attendance status
• Use cases: Ensure refreshments are work-related, control after-hours access
• Integration: Works with RFID attendance tracking system
        
Useful for companies that want to limit vending access to working hours.""",
        tracking=True,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_daily_limit = fields.Float(
        string='Daily Spending Limit',
        help="""Maximum amount employee can spend per day on vending purchases.
        
• Purpose: Control daily expenditure and prevent excessive spending
• Calculation: Based on 'Daily Limit Type' setting (24h or calendar day)
• Enforcement: Purchases blocked when daily limit is reached
• Reset: Automatically resets according to the selected time period
• No limit: Set to 0 to disable daily spending restrictions
        
Helps manage employee spending habits and company vending costs.""",
        default=0.0,
        groups="hr_rfid_vending.group_customer",
    )

    daily_limit_type = fields.Selection(
        selection=[
            ('last_24', 'Last 24 hours'),
            ('day', 'Current Calendar day'),
        ],
        string='Daily Limit Type',
        help="""How to calculate the daily spending period.
        
• Last 24 hours: Rolling 24-hour window from current time
• Current Calendar day: From midnight to midnight (calendar day)
        
Choose based on your organization's preferred spending control method.""",
        default='day',
        groups="hr_rfid_vending.group_customer",
    )
    hr_rfid_vending_spent_today = fields.Monetary(
        string='Spent Today',
        compute='_compute_spend_today',
        help="Amount already spent today based on the daily limit type setting. "
             "Used to calculate remaining daily allowance.",
        groups="hr_rfid_vending.group_customer",
    )
    hr_rfid_vending_current_balance = fields.Monetary(
        string='Available Balance',
        compute='_compute_current_balance',
        help="Total amount currently available for vending purchases. Combines company balance, "
             "personal balance, credit limits, and daily spending restrictions.",
        groups="hr_rfid_vending.group_customer",
    )
    currency_id = fields.Many2one(string='Company Currency', readonly=True,
                                  related='company_id.currency_id')

    hr_rfid_vending_auto_refill = fields.Boolean(
        string='Enable Auto Refill',
        help="""Automatically add money to employee's vending balance on a monthly schedule.
        
• Frequency: Runs according to company's auto-refill schedule settings
• Amount: Controlled by 'Refill Amount' and 'Refill Type' settings below
• Automation: No manual intervention required once configured
• Tracking: All auto-refills are logged in balance history
        
Useful for providing regular employee refreshment allowances.""",
        default=False,
        tracking=True,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_refill_amount = fields.Monetary(
        string='Refill Amount',
        help="""Amount to add during each auto-refill cycle.
        
• Fixed type: Exact amount added each month regardless of current balance
• Up To type: Amount added to reach the maximum, never exceeding refill max
• Currency: Uses company's default currency
• Frequency: Applied according to company auto-refill schedule
        
Set the monthly allowance amount for this employee.""",
        default=0.0,
        tracking=True,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_refill_type = fields.Selection(
        selection=[('fixed', 'Fixed'), ('up_to', 'Up To')],
        string='Refill Type',
        help="""How the auto-refill amount is applied to the employee's balance.
        
• Fixed: Always adds the refill amount, regardless of current balance
  - Example: If refill amount is 50, always adds 50 each month
• Up To: Adds money only to reach the maximum, never exceeding refill max
  - Example: If refill max is 100 and current balance is 30, adds 50 (not full refill amount)
        
Choose based on whether you want fixed allowances or balance limits.""",
        default='fixed',
        tracking=True,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_refill_max = fields.Monetary(
        string='Refill Maximum',
        help="""Maximum balance that auto-refill will maintain (only for 'Up To' refill type).
        
• Purpose: Set ceiling for automatic balance refills
• Function: Auto-refill stops when balance reaches this amount
• Example: If max is 100 and balance is 90, only 10 will be added (not full refill amount)
• Only used: When refill type is set to 'Up To'
        
Prevents over-funding employee vending accounts.""",
        default=0.0,
        groups="hr_rfid_vending.group_customer",
    )

    hr_rfid_vending_balance_history = fields.One2many(
        'hr.rfid.vending.balance.history',
        'employee_id',
        string='Balance History',
        help="Complete history of all balance changes including purchases, refills, "
             "manual adjustments, and auto-refills for this employee.",
        groups="hr_rfid_vending.group_customer",
    )

    def employee_vending_balance_history_action(self):
        self.ensure_one()
        bh_action = self.env.ref('hr_rfid_vending.hr_rfid_vending_balance_history_action').sudo().read()[0]
        bh_action['domain'] = [('employee_id', '=', self.id)]
        return bh_action

    @api.depends('hr_rfid_vending_balance',
                 'hr_rfid_vending_negative_balance',
                 'hr_rfid_vending_daily_limit',
                 'hr_rfid_vending_spent_today',
                 'hr_rfid_vending_recharge_balance',
                 'hr_rfid_vending_limit')
    def _compute_current_balance(self):
        for e in self:
            e.hr_rfid_vending_current_balance = e.get_employee_balance()

    @api.depends('hr_rfid_vending_balance_history')
    def _compute_spend_today(self):
        for e in self:
            if self.daily_limit_type == 'last_24':
                spent_today = self.env['hr.rfid.vending.balance.history'].read_group(
                    domain=[
                        ('employee_id', '=', e.id),
                        ('balance_change', '<', 0),
                        ('create_date', '>=', fields.Datetime.now() - timedelta(hours=24)),
                        ('create_date', '<=', fields.Datetime.now()),
                    ],
                    fields=['balance_change'],
                    groupby=['employee_id']
                )
            else:
                spent_today = self.env['hr.rfid.vending.balance.history'].read_group(
                    domain=[
                        ('employee_id', '=', e.id),
                        ('balance_change', '<', 0),
                        ('create_date', '>=', datetime.combine(fields.Date.today(), time(0, 0, 0))),
                        ('create_date', '<=', datetime.combine(fields.Date.today(), time(23, 59, 59))),
                    ],
                    fields=['balance_change'],
                    groupby=['employee_id']
                )
            e.hr_rfid_vending_spent_today = 0 if spent_today == [] else abs(spent_today[0]['balance_change'])

    def get_employee_balance(self, controller=None):
        self.ensure_one()
        # Get Main balance
        balance = self.hr_rfid_vending_balance
        if self.hr_rfid_vending_negative_balance is True:
            balance += self.hr_rfid_vending_limit
        if self.hr_rfid_vending_in_attendance is True and self.attendance_state == 'checked_out':
            if controller is None:
                return 0
            return '0000', 0
        if self.hr_rfid_vending_daily_limit != 0:
            limit = self.hr_rfid_vending_daily_limit
            limit -= self.hr_rfid_vending_spent_today
            if limit < balance:
                balance = limit
        # if balance <= 0:
        #     if controller is None:
        #         return 0
        #     return '0000', 0
        # add self balance
        # balance += Decimal(str(self.hr_rfid_vending_recharge_balance))
        balance += self.hr_rfid_vending_recharge_balance
        if balance <= 0:
            if controller is None:
                return 0
            return '0000', 0

        if controller is None:
            return balance

        return controller._convert_balance_to_ctrl(balance)

    def hr_rfid_vending_add_to_balance(self, value: float, ev: int = 0):
        """
        Add to the balance of an employee
        :param value: How much to add/subtract to/from the balance. Can be a positive or negative number.
        :param ev: Event id, ignored if 0
        :return: Balance history if successful
        """
        bh_ids = self.env['hr.rfid.vending.balance.history']
        for e in self:
            new_vend_balance = e.hr_rfid_vending_balance + value
            new_recharge_balance = e.hr_rfid_vending_recharge_balance
            if new_vend_balance < 0 and abs(new_vend_balance) > abs(e.hr_rfid_vending_limit):
                new_recharge_balance -= abs(new_vend_balance) - abs(e.hr_rfid_vending_limit)
                new_vend_balance = -abs(e.hr_rfid_vending_limit)
            # Get from vending balance to self balance if self balance is negative. Not usual case!
            if new_vend_balance > 0 and new_recharge_balance < 0:
                if abs(new_recharge_balance) <= new_vend_balance:
                    new_vend_balance += new_recharge_balance
                    new_recharge_balance = 0
                elif abs(new_recharge_balance) > new_vend_balance:
                    new_vend_balance = 0
                    new_recharge_balance += new_vend_balance

            e.write({
                'hr_rfid_vending_balance': new_vend_balance,
                'hr_rfid_vending_recharge_balance': new_recharge_balance,
            })

            bh_dict = {
                'balance_change': value,
                'employee_id': e.id,
                'balance_result': e.hr_rfid_vending_balance,
            }
            if ev > 0:
                bh_dict['vending_event_id'] = ev
            bh_ids += self.env['hr.rfid.vending.balance.history'].create(bh_dict)
        return bh_ids

    def hr_rfid_vending_set_balance(self, value: float, max_add: float = 0, min_add: float = 0, ev: int = 0):
        """
        Set an employee's balance to a specific number, with the option of max_add
        :param value:
        :param max_add:
        :param min_add:
        :param ev: Event id, ignored if 0
        :return: Balance history on success
        """
        bh_ids = self.env['hr.rfid.vending.balance.history']
        for c in self:
            val = value - c.hr_rfid_vending_balance
            if max_add != 0 and val > max_add:
                val = max_add
            if min_add != 0 and val < min_add:
                val = min_add
            bh_ids += c.hr_rfid_vending_add_to_balance(val, ev)
        return bh_ids

    def hr_rfid_vending_purchase(self, cost: float, ev: int = 0):
        """
        Purchase a product. Subtracts the parameter "cost" from the employee's balance
        :param cost: How much to subtract
        :param ev: Event id, ignored if 0
        :return: Balance history on success
        """
        return self.hr_rfid_vending_add_to_balance(-cost, ev)

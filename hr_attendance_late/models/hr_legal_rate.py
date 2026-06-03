# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools


class HrLegalRate(models.Model):
    """Dated legal coefficient (labour-law rate or supplement).

    Generic, time-versioned store for statutory values that change with an
    effective date — overtime multipliers, night-shift supplement, minimum
    wage, etc. Modelled on the canonical Odoo EE pattern
    `hr.rule.parameter.value` (which is paywalled behind hr_payroll), so the
    same temporal lookup is available on Community.

    Lookup picks the most recent value whose ``date_from`` is on or before the
    work date, so historical periods keep their historical coefficient and a
    statutory change is applied by adding a new dated row — never by editing
    an existing one in place.
    """
    _name = 'hr.legal.rate'
    _description = 'Dated Legal Rate / Coefficient'
    _order = 'code, date_from desc'

    code = fields.Char(
        required=True, index=True,
        help="Stable identifier referenced by the cost calculation, e.g. "
             "'overtime_workday', 'overtime_weekend', 'overtime_holiday', "
             "'night_supplement', 'min_wage'. Free text so localisation "
             "modules can add their own coefficients.",
    )
    name = fields.Char(
        help="Human label for this coefficient, shown in the settings list "
             "(e.g. 'Overtime — rest day'). Optional; the code is the key.",
    )
    date_from = fields.Date(
        string="Valid From", required=True, index=True,
        help="Date this value takes legal effect. The cost calculation for a "
             "worked day uses the value with the latest Valid From on or "
             "before that day, so past periods are never recalculated with a "
             "newer coefficient.",
    )
    value = fields.Float(
        required=True, digits=(16, 4),
        help="Numeric coefficient. For overtime classes this is a multiplier "
             "of the hourly rate (1.5 = 150%, i.e. +50%); for additive "
             "supplements (night work) it is an amount per hour in the "
             "currency below.",
    )
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        help="Leave empty for a national/global rate that applies to every "
             "company. Set a company only to override the statutory value for "
             "that company specifically.",
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        help="Relevant only for additive amount coefficients (e.g. the "
             "night-shift supplement per hour). Multipliers ignore it.",
    )

    # Two partial indexes instead of one UNIQUE(code, date_from, company_id):
    # PostgreSQL treats NULL as distinct in a UNIQUE constraint, so a plain
    # 3-column unique would NOT stop duplicate GLOBAL rates (company_id IS
    # NULL) — and two effective global rows for the same code/date make the
    # lookup non-deterministic. Split by company-set vs global.
    _unique_company_rate = models.UniqueIndex(
        '(code, date_from, company_id) WHERE company_id IS NOT NULL',
        "A legal rate already exists for this code, effective date and company.",
    )
    _unique_global_rate = models.UniqueIndex(
        '(code, date_from) WHERE company_id IS NULL',
        "A global legal rate already exists for this code and effective date.",
    )

    @api.model
    @tools.ormcache('code', 'date', 'company_id')
    def _get_rate(self, code, date, company_id=None):
        """Return the coefficient for ``code`` effective on ``date``.

        Company-specific row wins over a global (company-less) row when both
        are effective. Returns 0.0 when no rate is configured — callers treat
        a missing overtime multiplier as "no premium" (1.0 must be seeded
        explicitly) and a missing supplement as "no supplement".

        Looked up in two explicit steps rather than one ordered query: in
        PostgreSQL ``ORDER BY company_id DESC`` puts NULL (global) first, which
        would let a global row shadow a company override. So we try the
        company row first, then fall back to global.
        """
        base = [('code', '=', code), ('date_from', '<=', date)]
        if company_id:
            rate = self.search(
                base + [('company_id', '=', company_id)],
                order='date_from desc', limit=1,
            )
            if rate:
                return rate.value
        rate = self.search(
            base + [('company_id', '=', False)],
            order='date_from desc', limit=1,
        )
        return rate.value if rate else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

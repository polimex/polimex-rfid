from odoo import fields, models, api


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _get_default_sites(self):
        if not(self.is_company or self.is_employee):
            return self.env.user.partner_id.site_ids

    site_ids = fields.Many2many(
        comodel_name='hr.rfid.site',
        string='Sites',
        default=_get_default_sites,
        help="""Sites where this person has access or is responsible for.
        
• For employees: Sites where they work or have access
• For visitors: Sites they are permitted to visit
• For companies: Sites they manage or have contracts with

This affects which access groups are available for assignment."""
    )
    # all_site_ids = fields.Many2many(
    #     comodel_name='hr.rfid.site',
    #     string='All Sites',
    #     compute='_compute_all_site_ids'
    # )

    @api.onchange('site_ids')
    def onchange_site_ids(self):
        access_group_ids = self.site_ids.mapped('access_group_ids')
        # access_group_ids = self.env['hr.rfid.access.group']
        return {'domain': {'hr_rfid_access_group_ids.access_group_id': [('id', 'in', access_group_ids.ids)]}}
         # for p in self.site_ids:
        #     if not p.hr_rfid_access_group_ids:
        #         p.hr_rfid_access_group_ids += p.site_ids.access_group_ids and p.site_ids.access_group_ids.mapped('access_group_id') or access_group_ids
#
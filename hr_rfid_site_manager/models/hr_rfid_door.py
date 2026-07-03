from odoo import fields, models, api

class HrRFIDDoor(models.Model):
    _inherit = 'hr.rfid.door'

    site_id = fields.Many2one(
        'hr.rfid.site',
        string='Site',
        ondelete='set null',
        help="Physical site where this door is located. Doors are automatically included "
             "in site access groups and used for hierarchical access control."
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Create new doors and update access groups on related sites
        doors = super().create(vals_list)
        sites = doors.mapped('site_id')
        if sites:
            sites._update_access_groups()
        return doors

    def write(self, vals):
        # Remember original sites before changes
        old_sites = self.mapped('site_id')
        res = super().write(vals)
        # Gather sites after changes (including moved doors)
        new_sites = self.mapped('site_id')
        # Update access groups for all affected sites
        (old_sites | new_sites)._update_access_groups()
        return res

    def unlink(self):
        # Remember sites before deletion
        sites = self.mapped('site_id')
        res = super().unlink()
        # Update access groups for those sites
        if sites:
            sites._update_access_groups()
        return res

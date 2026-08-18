from odoo import fields, models, api, _
from odoo.api import ondelete
from odoo.exceptions import UserError


class HrRFIDAccessGroup(models.Model):
    _inherit = 'hr.rfid.access.group'

    site_id = fields.Many2one(
        'hr.rfid.site',
        string='Site',
        ondelete='cascade',
        help="Site that owns this access group. The group automatically includes all doors "
             "from this site and its child sites. Deleted when the site is deleted."
    )

    def update_door_list(self, door_ids, time_schedule=None, alarm_rights=False):
        for ag in self:
            # extract doors not already in the access group
            new_door_ids = door_ids - ag.door_ids.mapped('door_id')
            # extract doors that are not in the new list
            removed_door_ids = ag.door_ids.mapped('door_id') - door_ids
            if new_door_ids:
                ag.add_doors(new_door_ids, time_schedule, alarm_rights)
            if removed_door_ids:
                ag.del_doors(removed_door_ids)
        pass

    def unlink(self):
        for record in self:
            if record.site_id and record.site_id.make_access_group:
                raise UserError(_("You cannot delete an access group that is linked to a site."))
        return super(HrRFIDAccessGroup, self).unlink()

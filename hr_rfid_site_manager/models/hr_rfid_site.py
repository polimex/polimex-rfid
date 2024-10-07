from odoo import fields, models, api, _
from odoo.api import ondelete
from odoo.exceptions import UserError


class HrRFIDSite(models.Model):
    _name = 'hr.rfid.site'
    _description = 'Building manager site classification'
    _inherit = ['mail.thread', 'avatar.mixin']
    _rec_names_search=['name', 'parent_id']

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True)
    color = fields.Integer('Color Index', default=0)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    make_access_group = fields.Boolean('Make access group', default=False)
    parent_id = fields.Many2one(
        comodel_name='hr.rfid.site', string='Parent site' , ondelete='restrict')
    child_ids = fields.One2many(
        comodel_name='hr.rfid.site', inverse_name='parent_id', string='Child sites')
    webstack_ids = fields.One2many(
        comodel_name='hr.rfid.webstack', inverse_name='site_id', string='Modules')
    controller_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl', inverse_name='site_id', string='Controllers')
    door_ids = fields.One2many(
        comodel_name='hr.rfid.door', inverse_name='site_id', string='Doors')
    child_door_ids = fields.One2many(
        comodel_name='hr.rfid.door', compute='_compute_child_door_ids', string='Child doors')
    access_group_ids = fields.One2many(
        comodel_name='hr.rfid.access.group', inverse_name='site_id', string='Access groups')

    _sql_constraints = [
        ('no_loop', 'check(id != parent_id)', _('You cannot create a loop in the site hierarchy.')),
        ('unique_name', 'unique(name, company_id)', _('The site name must be unique.')),
    ]

    @api.depends('parent_id', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.parent_id:
                record.display_name = f"{record.parent_id.display_name} / {record.name}"
            else:
                record.display_name = record.name

    def get_child_access_groups(self):
        result =  self.env['hr.rfid.access.group']
        for site in self:
            for child in site.child_ids:
                result |= child.access_group_ids + child.get_child_access_groups()
                result |= child.get_child_access_groups()
        return result

    def _make_access_group(self):
        self.ensure_one()
        if self.access_group_ids:
            return self.access_group_ids
        self.access_group_ids = [(0, 0, {'name': _('%s group', self.display_name)})]
        return self.access_group_ids

    @api.depends('child_ids', 'door_ids', 'make_access_group')
    def _compute_child_door_ids(self):
        for site in self:
            if site.child_ids:
                site.child_door_ids = site.child_ids.mapped('door_ids') + site.child_ids.mapped('child_door_ids')
            else:
                site.child_door_ids = self.env['hr.rfid.door']
            # if site.parent_id:
            #     site.parent_id._compute_child_door_ids()
            # if site.make_access_group:
            #     site.access_group_ids.update_door_list(site.door_ids + site.child_door_ids)

    def create(self, vals_list):
        site = super(HrRFIDSite, self).create(vals_list)
        if site.make_access_group:
            site._make_access_group().update_door_list(site.door_ids + site.child_door_ids)
        return site

    def write(self, vals):
        res = super(HrRFIDSite, self).write(vals)
        if 'make_access_group' in vals or 'door_ids' in vals or 'child_ids' in vals:
            for site in self:
                if site.make_access_group and not site.access_group_ids:
                    site._make_access_group()
                elif not site.make_access_group and site.access_group_ids:
                    site.access_group_ids.unlink()
                if site.make_access_group:
                    site.access_group_ids.update_door_list(site.door_ids + site.child_door_ids)
        return res

    def get_children_site_ids(self):
        return self.env['hr.rfid.site'].search([('id', 'child_of', self.ids)])

    def get_site_hierarchy(self):
        if not self:
            return {}

        hierarchy = {
            'parent': {
                'id': self.parent_id.id,
                'name': self.parent_id.name,
                'doors': len(self.parent_id.door_ids),
            } if self.parent_id else False,
            'self': {
                'id': self.id,
                'name': self.name,
                'doors': len(self.door_ids),
            },
            'children': [
                {
                    'id': child.id,
                    'name': child.name,
                    'doors': len(child.door_ids)
                } for child in self.child_ids
            ]
        }

        return hierarchy

    def open_door_list_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_door_action')
        action['domain'] = [('site_id', 'child_of', self.id)]
        return action

    def open_controller_list_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_ctrl_action')
        action['domain'] = [('site_id', 'child_of', self.id)]
        return action

    def open_webstack_list_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_webstack_action')
        action['domain'] = [('site_id', 'child_of', self.id)]
        return action

    def open_access_group_list_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_access_group_action')
        action['domain'] = [('site_id', 'child_of', self.id)]
        return action
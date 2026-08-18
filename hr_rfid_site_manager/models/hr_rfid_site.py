from odoo import fields, models, api, _
from odoo.api import ondelete
from odoo.exceptions import UserError


class HrRFIDSite(models.Model):
    _name = 'hr.rfid.site'
    _description = 'Building manager site classification'
    _inherit = ['mail.thread', 'avatar.mixin']
    _rec_names_search=['name', 'parent_id']
    _parent_store = True



    name = fields.Char(
        required=True,
        help="Name of the site (building, floor, room, etc.). Must be unique within the parent site."
    )
    active = fields.Boolean(
        "Active", 
        default=True,
        help="Uncheck to archive this site. Archived sites are hidden from most views but preserve historical data."
    )
    color = fields.Integer(
        'Color Index', 
        default=0,
        help="Color coding for visual identification in hierarchy view. Choose different colors to distinguish site types or importance levels."
    )
    company_id = fields.Many2one(
        'res.company', 
        'Company', 
        default=lambda self: self.env.company,
        help="Company that owns this site. Used for multi-company access control and data separation."
    )
    make_access_group = fields.Boolean(
        'Make access group', 
        default=False,
        help="""Automatically create and maintain an access group for this site.
        
• When enabled: Creates an access group containing all doors in this site and child sites
• Access control: Assign people to this group to grant access to all site doors
• Automatic updates: Door changes automatically update the access group

Useful for: Building access, department access, or hierarchical permissions."""
    )
    parent_path = fields.Char(index=True)
    parent_id = fields.Many2one(
        comodel_name='hr.rfid.site', 
        string='Parent site', 
        ondelete='restrict',
        help="Parent site in the hierarchy. For example: Building > Floor > Room. "
             "Leave empty for top-level sites. Prevents deletion if child sites exist."
    )
    child_ids = fields.One2many(
        comodel_name='hr.rfid.site', 
        inverse_name='parent_id', 
        string='Child sites',
        help="Sites that are hierarchically below this site. For example: floors within a building, "
             "or rooms within a floor. Child sites inherit access permissions when using access groups."
    )
    webstack_ids = fields.One2many(
        comodel_name='hr.rfid.webstack', 
        inverse_name='site_id', 
        string='Modules',
        help="RFID communication modules (webstacks) installed at this site. "
             "Each module can manage multiple controllers and provides network connectivity."
    )
    controller_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl', 
        inverse_name='site_id', 
        string='Controllers',
        help="RFID controllers located at this site. Controllers manage individual doors "
             "and readers, handling access control decisions and event logging."
    )
    door_ids = fields.One2many(
        comodel_name='hr.rfid.door', 
        inverse_name='site_id', 
        string='Doors',
        help="Physical doors and access points at this site. Each door can have "
             "entry and exit readers for tracking person movement and access control."
    )
    child_door_ids = fields.One2many(
        comodel_name='hr.rfid.door', 
        compute='_compute_child_door_ids', 
        string='Child doors',
        help="All doors from child sites, computed automatically. Used for hierarchical access "
             "control - when creating access groups, doors from child sites are included."
    )
    access_group_ids = fields.One2many(
        comodel_name='hr.rfid.access.group', 
        inverse_name='site_id', 
        string='Access groups',
        help="Access control groups automatically created for this site. Groups contain all doors "
             "from this site and child sites. Assign people to these groups to grant site access."
    )
    # time_schedule = None, alarm_rights = False
    alarm_line_group_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm.group', 
        inverse_name='site_id', 
        string='Alarm Groups',
        help="Security alarm groups configured for this site. Used for arming/disarming "
             "security systems and managing intrusion detection across the site."
    )
    state = fields.Selection(
        related='alarm_line_group_ids.state', 
        string='Alarm Group State',
        help="Current security state of alarm groups at this site. Shows whether security "
             "systems are armed or disarmed. Changes automatically when alarm state changes."
    )

    child_count = fields.Integer(
        compute='_compute_count', 
        string="Child Count",
        help="Number of child sites under this site in the hierarchy."
    )
    webstack_count = fields.Integer(
        compute='_compute_count', 
        string="Module Count",
        help="Number of RFID communication modules (webstacks) at this site."
    )
    controller_count = fields.Integer(
        compute='_compute_count', 
        string="Controller Count",
        help="Number of RFID controllers at this site."
    )
    door_count = fields.Integer(
        compute='_compute_count', 
        string="Door Count",
        help="Number of doors and access points at this site."
    )
    access_group_count = fields.Integer(
        compute='_compute_count', 
        string="Access Group Count",
        help="Number of access control groups created for this site."
    )
    alarm_line_group_count = fields.Integer(
        compute='_compute_count', 
        string="Alarm Line Group Count",
        help="Number of security alarm groups configured for this site."
    )

    _sql_constraints = [
        ('no_loop', 'check(id != parent_id)', _('You cannot create a loop in the site hierarchy.')),
        ('unique_name', 'unique(name, parent_id, company_id)', _('The site name must be unique.')),
    ]

    @api.depends('child_ids', 'webstack_ids', 'controller_ids', 'door_ids', 'access_group_ids', 'alarm_line_group_ids')
    def _compute_count(self):
        for site in self:
            site.child_count = len(site.child_ids)
            site.webstack_count = len(site.webstack_ids)
            site.controller_count = len(site.controller_ids)
            site.door_count = len(site.door_ids)
            site.access_group_count = len(site.access_group_ids)
            site.alarm_line_group_count = len(site.alarm_line_group_ids)

    @api.depends('parent_id', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.parent_id:
                record.display_name = f"{record.parent_id.display_name} / {record.name}"
            else:
                record.display_name = record.name

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

    def create_child(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Site',
            'res_model': 'hr.rfid.site',
            'view_mode': 'form',
            'context': {'default_parent_id': self.id},
        }


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

    def _update_access_groups(self):
        for site in self:
            # 1) Създай или премахни собствената група
            if site.make_access_group and not site.access_group_ids:
                site._make_access_group()
            elif not site.make_access_group and site.access_group_ids:
                site.access_group_ids.unlink()
            # 2) Събери всички врати (директни + от дъщери)
            doors = site.door_ids + site.child_door_ids
            # 3) Обнови собствената група, ако е активирана
            if site.make_access_group:
                site.access_group_ids.update_door_list(doors)
            # 4) Рекурсивно обнови групата на родителя
            if site.parent_id:
                site.parent_id._update_access_groups()

    def create(self, vals_list):
        site = super(HrRFIDSite, self).create(vals_list)
        # Създаваме и собствената група, ако е нужно
        if site.make_access_group:
            site._make_access_group()
        # Обновяваме вратите и в групата на всички предци
        site.access_group_ids.update_door_list(site.door_ids + site.child_door_ids)
        site.partner_access_group().update_door_list(site.door_ids + site.child_door_ids)
        return site

    def partner_access_group(self):
        self.ensure_one()
        if not self.parent_id:
            return self.env['hr.rfid.access.group']
        else:
            return self.parent_id.partner_access_group() + self.parent_id.access_group_ids

    def write(self, vals):
        res = super(HrRFIDSite, self).write(vals)
        # Ако сменяме опцията за групи, вратите или йерархията:
        if any(f in vals for f in ('make_access_group', 'door_ids', 'child_ids')):
            for site in self:
                # Създаваме/премахваме собствената група
                if site.make_access_group and not site.access_group_ids:
                    site._make_access_group()
                elif not site.make_access_group and site.access_group_ids:
                    site.access_group_ids.unlink()
                # Обновяваме вратите в собствената група (ако има такава)
                if site.make_access_group:
                    site.access_group_ids.update_door_list(site.door_ids + site.child_door_ids)
                # И задължително обновяваме групите на всички предци
                site.partner_access_group().update_door_list(site.door_ids + site.child_door_ids)
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

    def open_child_site_list_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_rfid_site_manager.hr_rfid_site_action')
        action['domain'] = [('parent_id', '=', self.id)]
        return action

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

    def open_alarm_line_group_list_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_ctrl_alarm_group_action')
        action['domain'] = [('site_id', 'child_of', self.id)]
        return action

    def arm(self):
        return self.alarm_line_group_ids.arm()

    def disarm(self):
        return self.alarm_line_group_ids.disarm()
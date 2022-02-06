from odoo import fields, models, api


class AliasMixin(models.AbstractModel):
    """ A mixin for models that need to return balloon msg in backend.
    """
    _name = 'balloon.mixin'
    _description = 'Balloon Messages Mixin'

    @api.model
    def balloon_success(self, title: str, message: str, links: [dict] = None, sticky: bool = False):
        return self.balloon(title, message, links, sticky=sticky)

    @api.model
    def balloon_success_sticky(self, title: str, message: str, links: [dict] = None):
        return self.balloon(title, message, links, sticky=True)

    @api.model
    def balloon_warning(self, title: str, message: str, links: [dict] = None, sticky: bool = False):
        return self.balloon(title, message, links, type='warning', sticky=sticky)

    @api.model
    def balloon_warning_sticky(self, title: str, message: str, links: [dict] = None):
        return self.balloon(title, message, links, type='warning', sticky=True)

    @api.model
    def balloon_danger(self, title: str, message: str, links: [dict] = None, sticky: bool = False):
        return self.balloon(title, message, links, type='danger', sticky=sticky)

    @api.model
    def balloon_danger_sticky(self, title: str, message: str, links: [dict] = None):
        return self.balloon(title, message, links, type='danger', sticky=True)

    @api.model
    def balloon(self, title: str, message: str, links: [dict] = None, type: str = 'success', sticky: bool = False):
        '''
        Return action for message in balloon.
        Required: title, message
        Optional:
            links like:
                [{'label': cmd_id.name,
                  'model': 'hr.rfid.command',
                  'res_id': cmd.id,
                  'action': 'hr_rfid.hr_rfid_command_action'
                }]
            type: success(default), danger, warning
            sticky: bool (default False)

        '''
        action = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': type,
                'sticky': sticky,
            }}
        if links:
            f_links = []
            for l in links:
                action = self.env.ref(l['action']).sudo()
                f_links.append({
                    'label': l['label'],
                    'url' : f"#action={action.id}&id={l['res_id']}&model={l['model']}&view_type=form"
                })
            action['params']['links']=f_links
        return action

        # cmd_id = cmd_env.create([cmd_dict])
        # action = self.env.ref('	hr_rfid.hr_rfid_command_action').sudo()
        # {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': _('Command creation successful'),
        #         'message': _(
        #             'Because the webstack is behind NAT, we have to wait for the webstack to call us, so we created a command. The door will open/close as soon as possible.'),
        #         'links': [{
        #             'label': cmd_id.name,
        #             'url': f'#action={action.id}&id={cmd_id.id}&model=hr.rfid.command&view_type=form'
        #         }],
        #         'type': 'warning',
        #         'sticky': False,
        #     }}

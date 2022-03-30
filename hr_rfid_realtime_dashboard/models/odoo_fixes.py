from odoo import fields, models, api, http

'''
Bug Info
https://www.odoo.com/es_ES/forum/ayuda-1/custom-dashboard-error-edit-custom-missing-1-required-positional-argument-custom-id-168550

'''

class View(http.Controller):

    @http.route('/web/view/edit_custom', type='json', auth="user")
    def edit_custom(self, **kw):
        if kw.get('custom_id'):
            custom_view = http.request.env['ir.ui.view.custom'].browse(kw.get('custom_id'))
            custom_view.write({'arch': kw.get('arch')})
        return {'result': True}

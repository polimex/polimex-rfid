from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        if 'list_price' not in vals:
            return super(ProductTemplate, self).write(vals)


        # rec stands for record
        for rec in self:
            old_list_price = rec.list_price
            super(ProductTemplate, rec).write(vals)
            new_list_price = rec.list_price

            if old_list_price != new_list_price:
                ret = self.env['hr.rfid.ctrl.vending.row'].search([
                    '|', '|', '|',
                        ('item1', '=', rec.id),
                        ('item2', '=', rec.id),
                        ('item3', '=', rec.id),
                        ('item4', '=', rec.id),
                ])
                if len(ret) == 0:
                    continue
                for ctrl in ret:
                    wiz = self.env['hr.rfid.ctrl.vending.settings'].with_context(active_ids=[ctrl.controller_id.id]).create({})
                    wiz.save_settings()

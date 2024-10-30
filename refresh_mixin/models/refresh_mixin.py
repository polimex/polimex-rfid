from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class RefreshMixin(models.AbstractModel):
    """ A mixin for models that need to refresh the views.
    """
    _name = 'refresh.mixin'
    _description = 'Model Refresh Mixin'
    _refresh_on_create = False
    _refresh_on_write = True

    def get_company_id(self):
        if 'company_id' not in self._fields:
            _logger.warning('Model %s does not have company_id field', self._name)
            return self.env.company.id or 0
        return self.company_id.id

    def send_notice(self, operation):
        # check if model have field company_id
        company_id = self.get_company_id()
        self.env['bus.bus']._sendone(
            f'polimex.{self._name}',
            f'polimex.{self._name}.record_changed' if operation == 'write' else f'polimex.{self._name}.record_created',
            {'record_ids': self.ids,
             'company_id': company_id,
             'model': self._name,
             }
        )
        _logger.info('Model Refresh on write on channel %s', f'polimex.{self._name}')

    def write(self, vals):
        res = super().write(vals)
        if self._refresh_on_write:
            self.send_notice('write')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if self._refresh_on_create:
            res.send_notice('create')
        return res



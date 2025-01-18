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
        if 'company_id' in self._fields:
            return self.company_id

    def send_notice(self, operation):
        # check if model have field company_id
        company_id = self.get_company_id()
        if not company_id:
            _logger.warning('Model %s does not have company_id field', self._name)
            return
        if not company_id.realtime_refresh:
            return # do not send notice if company is not in realtime mode
        self.env['bus.bus']._sendone(
            f'polimex.{self._name}',
            f'polimex.{self._name}.record_changed' if operation == 'write' else f'polimex.{self._name}.record_created',
            {'record_ids': self.ids,
             'company_id': company_id.id,
             'model': self._name,
             }
        )
        # _logger.info('Model Refresh on write on channel %s', f'polimex.{self._name}')

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



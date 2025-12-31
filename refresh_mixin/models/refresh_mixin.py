from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class RefreshMixin(models.AbstractModel):
    """
    A mixin for models that need to refresh dashboard views via bus notifications.

    Features:
    - Automatic bus notification on create/write
    - Configurable refresh behavior per model
    - Extended payload support for alert detection
    - Throttle-friendly design (frontend handles throttling)

    Usage:
        class MyModel(models.Model):
            _name = 'my.model'
            _inherit = ['refresh.mixin']
            _refresh_on_create = True  # Send bus notification on create
            _refresh_on_write = True   # Send bus notification on write (default)

            # Optional: Override to add custom payload data
            def _get_refresh_payload_extra(self):
                return {'is_alert': self.is_urgent, 'priority': self.priority}
    """
    _name = 'refresh.mixin'
    _description = 'Model Refresh Mixin'
    _refresh_on_create = False
    _refresh_on_write = True

    def get_company_id(self):
        """Get company_id for the record(s). Returns first company if multiple records."""
        if 'company_id' in self._fields:
            return self.company_id
        return False

    def _get_refresh_payload_extra(self):
        """
        Override this method in models to add extra data to the bus payload.
        Useful for sending alert information, event types, etc.

        Returns:
            dict: Extra payload data to merge with base payload

        Example:
            def _get_refresh_payload_extra(self):
                # For ichecker.event model
                return {
                    'is_alert': self.service_id.is_panic_button,
                    'event_type': self.event_type,
                    'service_name': self.service_id.name,
                }
        """
        return {}

    def send_notice(self, operation):
        """
        Send bus notification for dashboard refresh.

        Args:
            operation (str): 'create' or 'write'
        """
        # Check if model has company_id field
        company_id = self.get_company_id()
        if not company_id:
            _logger.warning('Model %s does not have company_id field', self._name)
            return

        # Check if company has realtime refresh enabled
        if not company_id.realtime_refresh:
            return  # Do not send notice if company is not in realtime mode

        # Build base payload
        payload = {
            'record_ids': self.ids,
            'company_id': company_id.id,
            'model': self._name,
            'operation': operation,
        }

        # Add extra payload data from model (e.g., alert info)
        try:
            extra = self._get_refresh_payload_extra()
            if extra:
                payload.update(extra)
        except Exception as e:
            _logger.warning('Error getting extra payload for %s: %s', self._name, e)

        # Send bus notification
        channel = f'polimex.{self._name}'
        notification_type = f'polimex.{self._name}.record_changed' if operation == 'write' else f'polimex.{self._name}.record_created'

        self.env['bus.bus']._sendone(channel, notification_type, payload)
        _logger.debug('Refresh notification sent: %s -> %s', notification_type, payload)

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



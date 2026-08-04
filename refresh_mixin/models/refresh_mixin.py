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

    def get_company_ids(self):
        """Every company that should receive the realtime refresh for these
        records. Defaults to the single company from :meth:`get_company_id`;
        override when a record concerns more than one company (e.g. hardware
        shared between companies)."""
        company_id = self.get_company_id()
        return company_id or self.env['res.company']

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
        # Resolve the companies these records concern. An empty result is
        # expected control flow — a global record, or an event whose
        # company-bearing relations are all empty — for which the realtime
        # refresh is simply skipped. That is not an operator-actionable
        # problem, so it is logged at debug (silent by default) rather than
        # flooding the log with a WARNING on every such create/write.
        companies = self.get_company_ids()
        if not companies:
            _logger.debug(
                'No company resolved for %s %s; skipping realtime refresh',
                self._name, self.ids)
            return

        # Notify only the companies that have realtime refresh enabled.
        # sudo: a shared record legitimately concerns companies the acting
        # user is not allowed to read (res.company is restricted to the
        # user's own companies), and reading their flag must not raise.
        companies = companies.sudo().filtered('realtime_refresh')
        if not companies:
            return

        # Build base payload. `company_id` stays for backward compatibility
        # with clients that predate the multi-company `company_ids` list.
        payload = {
            'record_ids': self.ids,
            'company_id': companies[0].id,
            'company_ids': companies.ids,
            'model': self._name,
            'operation': operation,
        }

        # Add extra payload data from model (e.g., alert info). A faulty
        # override must not block the core refresh, but the traceback has to
        # survive — otherwise a broken _get_refresh_payload_extra() silently
        # drops its enrichment (is_alert/priority/...) with no way to diagnose.
        try:
            extra = self._get_refresh_payload_extra()
            if extra:
                payload.update(extra)
        except Exception:
            _logger.warning(
                'Error building extra refresh payload for %s %s; '
                'sending base payload only', self._name, self.ids, exc_info=True)

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



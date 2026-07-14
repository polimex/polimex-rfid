# -*- coding: utf-8 -*-
"""Real-time delivery of ``hr.rfid.command`` over the websocket channel.

The command QUEUE stays exactly what it is today (Wait/Process + retries,
delivered in the HTTP response whenever the module polls) - the bus is a
TRANSPORT, never the persistent copy (ODOO_BUS_ARCHITECTURE.md §3.2).
This file only adds the low-latency path:

- a command created while its module is real-time online is published
  immediately (seconds instead of the next poll);
- a re-publish cron covers lost bus messages for connected modules;
- everything else (offline modules, disabled channel, legacy firmware)
  keeps flowing through ``check_for_unsent_cmd`` untouched.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# How long a published command may stay unanswered before the cron
# re-publishes it (ARCHITECTURE §10.1 proposal). Retries share the same
# counter/limit as the HTTP retry path.
WS_CMD_REPUBLISH_TIMEOUT_S = 15
WS_CMD_MAX_RETRIES = 5


class HrRfidCommandWs(models.Model):
    _inherit = 'hr.rfid.command'

    @api.model_create_multi
    def create(self, vals_list):
        commands = super().create(vals_list)
        if self.env.context.get('ws_no_publish'):
            # the event-batch path carries the spawned command INLINE in the
            # ev_ack (SPEC §6.3) - a parallel publish would only duplicate it
            return commands
        for command in commands:
            webstack = command.webstack_id
            # One-command-in-flight (owner rule): publish immediately ONLY
            # when nothing is outstanding on this module - the device stages
            # at most 4 commands (e=24 NO_QUADRANT on overflow, INTEROP
            # 2026-07-13). A command left in Wait is chained by
            # _ws_publish_next_command when the in-flight one answers.
            if (command.status == 'Wait' and webstack
                    and webstack.sudo().ws_enabled and webstack.ws_online
                    and not webstack.sudo().in_cmd_execution()):
                # The real-time publish is best-effort transport: it must NEVER
                # break the business transaction that created the command (a
                # card write, an access-group change). On failure the command
                # stays Wait -> the HTTP piggyback / next sync delivers it (F6).
                try:
                    webstack._ws_publish_command(command)
                except Exception:
                    _logger.warning(
                        'WS: could not publish new command %s (%s) to module '
                        '%s; it stays queued for the classic delivery.',
                        command.id, command.cmd, webstack.serial, exc_info=True)
        return commands

    @api.model
    def _ws_republish_cron(self):
        """Re-publish commands stuck in Process on real-time-online modules.

        Covers a lost ``hr_rfid.cmd`` bus message or a device that dropped
        between the publish and its response. Shares the retries counter and
        the 5-attempt limit with the HTTP retry path; a module that fell
        back to HTTP is skipped here (its next poll retries via
        ``check_for_unsent_cmd`` as always).
        """
        cutoff = fields.Datetime.now() - timedelta(seconds=WS_CMD_REPUBLISH_TIMEOUT_S)
        commands = self.sudo().search([
            ('status', '=', 'Process'),
            ('write_date', '<', cutoff),
            ('webstack_id.ws_enabled', '=', True),
        ])
        for command in commands:
            webstack = command.webstack_id
            if not webstack.ws_online:
                continue
            if command.retries >= WS_CMD_MAX_RETRIES:
                # Permanent delivery failure - persist it AND surface it to
                # the operator log (a silently dying command is invisible
                # until someone opens the command list).
                _logger.warning(
                    'Real-time delivery of command %s (%s) to module %s '
                    'gave up after %d attempts; marked Failure.',
                    command.id, command.cmd, webstack.serial, command.retries)
                command.write({'status': 'Failure',
                               'error': 'Real-time delivery gave up after '
                                        '%d attempts' % command.retries})
                continue
            # Count the attempt OUTSIDE the publish savepoint so a command that
            # keeps failing still climbs toward the give-up limit (otherwise a
            # poison command rolls back its own retries and starves the whole
            # cron forever - F5). The publish + its status flip are atomic per
            # command; one failure never aborts the others.
            command.retries += 1
            try:
                with self.env.cr.savepoint():
                    webstack._ws_publish_command(command)
            except Exception:
                _logger.warning(
                    'WS: re-publish of command %s (%s) to module %s failed '
                    '(attempt %d); will retry next cron.',
                    command.id, command.cmd, webstack.serial, command.retries,
                    exc_info=True)

# Polimex Holding Ltd. - https://polimex.co
"""Commands already in the queue get the rule new ones are created with.

A command that is handed over once - the routine clock setting and state
reading, the answer to "may this card pass" and the credit for a vending
machine - is marked so when it is created. The ones waiting or out at the
moment of the upgrade were created before the mark existed. Without this they
would be handed over again and again like any other command: a door released
minutes after it was asked for, a clock setting holding the queue for its five
attempts.
"""

import logging

from odoo.addons.hr_rfid.controllers.polimex import ROUTINE_COMMANDS

_logger = logging.getLogger(__name__)

# The answers of the moment: the credit for a vending machine (DB2) and the
# answer to a card shown at a door that asks the server (DB with data '40...').
VENDING_CREDIT = "DB2"
DOOR_ANSWER = "DB"
DOOR_ANSWER_DATA = "40%"


def migrate(cr, version):
    cr.execute(
        """
        UPDATE hr_rfid_command
           SET single_attempt = TRUE
         WHERE status IN ('Wait', 'Process')
           AND single_attempt IS NOT TRUE
           AND (cmd IN %s OR (cmd = %s AND cmd_data LIKE %s))
        """,
        (tuple(ROUTINE_COMMANDS) + (VENDING_CREDIT,), DOOR_ANSWER, DOOR_ANSWER_DATA),
    )
    _logger.info("hr_rfid: %s queued commands marked as handed over once", cr.rowcount)

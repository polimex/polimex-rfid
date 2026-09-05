"""The one place that decides which commands may leave this module.

A survey of a running system is only trustworthy if it can be PROVEN to read
and never write. The proof is structural: every command goes through
``check_allowed`` before a socket is touched, and the list is an ALLOWLIST -
an opcode that is not named here is refused, so a new or unknown opcode can
never slip through as "probably harmless".

The allowlist and the forbidden set below are the wire-level facts this module
needs; they live only here, in the codecs and in the tests.
"""

#: Opcodes that only read controller state. Everything else is refused.
READ_OPCODES = frozenset({
    'F0',  # system information
    'F1',  # one card by number
    'F2',  # card table (count / page)
    'F3',  # time schedule by slot
    'F4',  # holiday list by slot
    'F5',  # controller mode
    'F6',  # reader modes
    'F7',  # clock
    'F8',  # duress
    'F9',  # input/output table
    'FB',  # input masks
    'FC',  # anti-passback settings
    'FF',  # output time schedules
    'B3',  # live status
})

#: The alarm-setup opcode is read/write on the same code; only the read form
#: (direction byte 01) is allowed.
ALARM_SETUP_OPCODE = 'B0'
ALARM_SETUP_READ_DATA = '01'

#: Slot ranges the controller accepts. Slot 0 of the time schedules is not a
#: schedule at all - the controller answers with its configuration page.
TIME_SCHEDULE_SLOTS = range(1, 16)
HOLIDAY_SLOTS = range(1, 9)

#: HTTP paths of the module's local interface the survey may call.
HTTP_GET_PATHS = frozenset({
    '/config.json',
    '/sdk/details.json',
    '/sdk/status.json',
    '/discovery.json',
})
HTTP_POST_PATHS = frozenset({'/sdk/cmd.json'})


class ForbiddenOpcode(Exception):
    """Raised BEFORE any network I/O for anything outside the allowlist."""

    def __init__(self, opcode, data=''):
        self.opcode = opcode
        self.data = data
        super().__init__(
            "Command %s (%s) is not a read command and is refused by the survey"
            % (opcode, data or 'no data'))


class ForbiddenPath(Exception):
    """Raised for an HTTP path the survey must never call."""


def _slot_of(data):
    try:
        return int((data or '')[:2] or '0', 16)
    except ValueError:
        return -1


def check_allowed(opcode, data=''):
    """Refuse everything that is not a read; return the normalised opcode."""
    op = (opcode or '').upper()
    data = (data or '').upper()
    if op == ALARM_SETUP_OPCODE:
        if data != ALARM_SETUP_READ_DATA:
            raise ForbiddenOpcode(op, data)
        return op
    if op not in READ_OPCODES:
        raise ForbiddenOpcode(op, data)
    if op == 'F3' and _slot_of(data) not in TIME_SCHEDULE_SLOTS:
        raise ForbiddenOpcode(op, data)
    if op == 'F4' and _slot_of(data) not in HOLIDAY_SLOTS:
        raise ForbiddenOpcode(op, data)
    return op


def check_http_path(method, path):
    """Refuse every module URL that is not part of the read-only interface."""
    bare = (path or '').split('?', 1)[0]
    if method.upper() == 'GET' and bare in HTTP_GET_PATHS:
        return bare
    if method.upper() == 'POST' and bare in HTTP_POST_PATHS:
        return bare
    raise ForbiddenPath("%s %s is not part of the read-only module interface"
                        % (method, path))

"""The one place that decides which commands may leave this module.

A survey of a running system is only trustworthy if it can be PROVEN to read
and never write. The proof is structural: every command goes through
``check_allowed`` before a socket is touched, and the list is an ALLOWLIST -
an opcode that is not named here is refused, so a new or unknown opcode can
never slip through as "probably harmless".

The allowlist and the forbidden set below are the wire-level facts this module
needs; they live only here, in the codecs and in the tests.

The module address is part of the same proof: it is glued into the URL, so an
"address" carrying a path or a query would reach a page outside the list. Only
a bare IP address or host name passes ``check_host``.
"""

import ipaddress
import re

#: Opcodes that only read controller state. Everything else is refused.
READ_OPCODES = frozenset(
    {
        "F0",  # system information
        "F1",  # one card by number
        "F2",  # card table (count / page)
        "F3",  # time schedule by slot
        "F4",  # holiday list by slot
        "F5",  # controller mode
        "F6",  # reader modes
        "F7",  # clock
        "F8",  # duress
        "F9",  # input/output table
        "FB",  # input masks
        "FC",  # anti-passback settings
        "FF",  # output time schedules
        "B3",  # live status
    }
)

#: The alarm-setup opcode is read/write on the same code; only the read form
#: (direction byte 01) is allowed.
ALARM_SETUP_OPCODE = "B0"
ALARM_SETUP_READ_DATA = "01"

#: Slot ranges the controller accepts. Slot 0 of the time schedules is not a
#: schedule at all - the controller answers with its configuration page.
TIME_SCHEDULE_SLOTS = range(1, 16)
HOLIDAY_SLOTS = range(1, 9)

#: HTTP paths of the module's local interface the survey may call.
HTTP_GET_PATHS = frozenset(
    {
        "/config.json",
        "/sdk/details.json",
        "/sdk/status.json",
        "/discovery.json",
    }
)
HTTP_POST_PATHS = frozenset({"/sdk/cmd.json"})

#: A host name as RFC 1123 allows it: dot-separated labels of letters, digits
#: and inner hyphens, at most 253 characters in all.
HOST_LABEL = re.compile(r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)")

#: A last label of digits only is never a host name (RFC 3696, section 2): the
#: system resolver reads "192.168.1" or "10.1" as a different IP address.
NUMERIC_LABEL = re.compile(r"[0-9]+")
HOST_MAX_LENGTH = 253


class ForbiddenOpcode(Exception):
    """Raised BEFORE any network I/O for anything outside the allowlist."""

    def __init__(self, opcode, data=""):
        self.opcode = opcode
        self.data = data
        super().__init__(
            "Command %s (%s) is not a read command and is refused by the survey"
            % (opcode, data or "no data")
        )


class ForbiddenPath(Exception):
    """Raised for an HTTP path the survey must never call."""


class ForbiddenHost(Exception):
    """Raised for a module address that is not a bare IP address or host name.

    ``reason`` says why, for the message the operator gets: 'not_host',
    'bad_ip' (numbers that are not a valid IP address: parts missing, extra
    parts, leading zeros) or 'zone' (an IPv6 zone).
    """

    def __init__(self, message, reason="not_host"):
        self.reason = reason
        super().__init__(message)


def _slot_of(data):
    try:
        return int((data or "")[:2] or "0", 16)
    except ValueError:
        return -1


def check_allowed(opcode, data=""):
    """Refuse everything that is not a read; return the normalised opcode."""
    op = (opcode or "").upper()
    data = (data or "").upper()
    if op == ALARM_SETUP_OPCODE:
        if data != ALARM_SETUP_READ_DATA:
            raise ForbiddenOpcode(op, data)
        return op
    if op not in READ_OPCODES:
        raise ForbiddenOpcode(op, data)
    if op == "F3" and _slot_of(data) not in TIME_SCHEDULE_SLOTS:
        raise ForbiddenOpcode(op, data)
    if op == "F4" and _slot_of(data) not in HOLIDAY_SLOTS:
        raise ForbiddenOpcode(op, data)
    return op


def check_host(host):
    """Refuse anything but a bare IP address or host name; return it in the
    form it takes inside a URL (an IPv6 address goes in brackets)."""
    host = (host or "").strip()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        labels = host.rstrip(".").split(".")
        if (
            not host
            or len(host) > HOST_MAX_LENGTH
            or not all(HOST_LABEL.fullmatch(label) for label in labels)
        ):
            raise ForbiddenHost(
                "%r is not an IP address or a host name" % host
            ) from None
        if NUMERIC_LABEL.fullmatch(labels[-1]):
            raise ForbiddenHost(
                "%r is not a valid IP address" % host, reason="bad_ip"
            ) from None
        return host
    if address.version == 6 and address.scope_id:
        # The zone of a link-local address accepts any text, brackets and
        # '@' included, which would turn the URL's host into something else.
        raise ForbiddenHost(
            "%r carries an IPv6 zone, which a module address never needs" % host,
            reason="zone",
        )
    return "[%s]" % address if address.version == 6 else str(address)


def check_http_path(method, path):
    """Refuse every module URL that is not part of the read-only interface."""
    bare = (path or "").split("?", 1)[0]
    if method.upper() == "GET" and bare in HTTP_GET_PATHS:
        return bare
    if method.upper() == "POST" and bare in HTTP_POST_PATHS:
        return bare
    raise ForbiddenPath(
        "%s %s is not part of the read-only module interface" % (method, path)
    )

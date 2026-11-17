"""How the survey talks to a module: plain HTTP to its local interface.

The module (the network gateway in front of the RS-485 controllers) exposes a
small local HTTP interface. The survey uses only its read side: the module
configuration, the list of controllers it sees, and the command relay that
forwards ONE controller command and returns the reply. The module is never
re-pointed, never rebooted and never given a new key from here.

Every command passes through :func:`allowlist.check_allowed` before a socket is
touched, every attempt is handed to ``on_log`` so the survey keeps an auditable
trail, and every reply is checked to be the reply to THIS command (a gateway
in passive mode can echo the previous reply for a few cycles).
"""

import logging
import time

import requests

from . import allowlist

_logger = logging.getLogger(__name__)

HTTP_TIMEOUT = (3, 10)
HTTP_TIMEOUT_IO_TABLE = (3, 15)

#: How many times a reply that belongs to another command is discarded before
#: the command is given up on.
SKEW_RETRIES = 8
SKEW_PAUSE = 0.5

#: Reply codes of the command relay. 0 is success; 1..14 come from the
#: controller; 20 and above from the gateway itself.
E_OK = 0
E_WRONG_VALUE = 4
E_BUSY = 12
E_UNKNOWN_COMMAND = 14
E_NO_RESPONSE = 20
E_BAD_JSON = 21
E_BAD_CRC = 22
E_BRIDGE_ACTIVE = 23
E_INTERNAL = 24

#: (retries, pause in seconds) for the codes that are worth waiting on.
RETRY_POLICY = {
    E_NO_RESPONSE: (3, (0.5, 1.0, 2.0)),
    E_BAD_CRC: (2, (0.5, 1.0)),  # a damaged frame on the bus; seen live on a fire panel
    E_BRIDGE_ACTIVE: (3, (5.0,) * 3),
    E_INTERNAL: (2, (1.0, 2.0)),
    E_BUSY: (3, (2.0,) * 3),
}

#: The most one command may take, retries and pauses included. The survey
#: runs inside a scheduled action with a hard time limit; a module that keeps
#: the survey waiting longer than this is reported, not waited for.
COMMAND_BUDGET_SECONDS = 45.0


class TransportError(Exception):
    """Base of everything this layer raises."""


class Unreachable(TransportError):
    """The module did not answer at all (network, HTTP, timeout, bad JSON).

    ``status`` carries the HTTP status code when there was one, so a caller can
    tell "this page does not exist on this firmware" from a real failure.
    ``kind`` names the class of failure for the operator-facing message the
    caller builds ('password', 'network', 'http', 'json', 'reply', 'skew' -
    answers meant for another command, 'address' - an address that is not a
    bare IP address or host name); the
    exception text itself is for the log.
    """

    def __init__(self, message, status=None, kind="network"):
        self.status = status
        self.kind = kind
        super().__init__(message)


class ReadFailed(TransportError):
    """The controller answered, but with an error that is not a capability gap."""

    def __init__(self, opcode, e_code, address=None):
        self.opcode = opcode
        self.e_code = e_code
        self.address = address
        super().__init__(
            "command %s to controller %s failed with code %s"
            % (opcode, address, e_code)
        )


class CapabilityGap(TransportError):
    """The controller does not implement this command; recorded, not fatal."""

    def __init__(self, opcode, e_code, address=None):
        self.opcode = opcode
        self.e_code = e_code
        self.address = address
        super().__init__(
            "command %s is not supported by controller %s (code %s)"
            % (opcode, address, e_code)
        )


class Reply:
    __slots__ = ("address", "opcode", "e", "data", "duration_ms", "attempts", "skewed")

    def __init__(self, address, opcode, e, data, duration_ms, attempts, skewed):
        self.address = address
        self.opcode = opcode
        self.e = e
        self.data = data
        self.duration_ms = duration_ms
        self.attempts = attempts
        self.skewed = skewed


class CoreDiscovery:
    """The network search of the access control module itself.

    ``hr.rfid.webstack.discovery._discover_ws`` sends the discovery datagram,
    collects the answers into rows of that wizard and touches no device; only
    its separate ``setup_modules`` writes, and that one is never called from
    here. Modules already registered in this database do not appear in its
    result; the survey lists those when they are added by address.
    """

    def __init__(self, env):
        self.env = env

    def broadcast(self):
        """Every unregistered module on the local network, as dicts.

        Raises OSError when the search itself cannot run (the port is held by
        another process, or the network does not allow broadcast)."""
        wizard = self.env["hr.rfid.webstack.discovery"].sudo()
        rows = (
            self.env["hr.rfid.webstack.discovery.row"]
            .sudo()
            .browse(wizard._discover_ws() or [])
        )
        return [
            {
                "ip": row.last_ip,
                "hostname": row.name,
                "hw_version": row.hw_version,
                "fw_version": row.version,
                "serial": row.serial,
            }
            for row in rows
        ]


class HardwareClient:
    """Read-only HTTP client for one module."""

    def __init__(
        self, host, port=80, auth=None, on_log=None, sleep=time.sleep, session=None
    ):
        self.host = host
        self.url_host = allowlist.check_host(host)
        self.port = port or 80
        self.auth = tuple(auth) if auth and auth[0] else None
        self.on_log = on_log
        self.sleep = sleep
        self.session = session or requests.Session()

    # ---------------------------------------------------------- HTTP plumbing

    def _url(self, path):
        return "http://%s:%s%s" % (self.url_host, self.port, path)

    def _payload(self, response, path):
        """The JSON object of a 200 answer; anything else is Unreachable with a
        message the operator can act on."""
        status = response.status_code
        if status in (401, 403):
            raise Unreachable(
                "%s requires a password for %s, or the password is wrong"
                % (self.host, path),
                status=status,
                kind="password",
            )
        if status != 200:
            # The module answers 404 for an unknown path and for a wrong method
            # alike; either way this is not a module we can read.
            raise Unreachable(
                "%s answered HTTP %s for %s" % (self.host, status, path),
                status=status,
                kind="http",
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise Unreachable(
                "%s did not return JSON for %s" % (self.host, path),
                status=status,
                kind="json",
            ) from exc
        if not isinstance(payload, dict):
            raise Unreachable(
                "%s returned an unexpected answer for %s" % (self.host, path),
                status=status,
                kind="json",
            )
        return payload

    def _get(self, path, params=None, timeout=HTTP_TIMEOUT):
        allowlist.check_http_path("GET", path)
        try:
            # A module never redirects; a redirect would be another host answering
            # in its place, and the survey must not follow it.
            response = self.session.get(
                self._url(path),
                params=params,
                auth=self.auth,
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise Unreachable("%s: %s" % (self.host, exc)) from exc
        return self._payload(response, path)

    def _post(self, path, payload, timeout=HTTP_TIMEOUT):
        allowlist.check_http_path("POST", path)
        try:
            response = self.session.post(
                self._url(path),
                json=payload,
                auth=self.auth,
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise Unreachable("%s: %s" % (self.host, exc)) from exc
        return self._payload(response, path)

    # ---------------------------------------------------------- module reads

    def get_config(self):
        return self._get("/config.json")

    def get_details(self):
        return self._get("/sdk/details.json")

    def get_status(self, dev):
        return self._get("/sdk/status.json", params={"dev": dev})

    def get_discovery(self):
        return self._get("/discovery.json")

    # ---------------------------------------------------------- controller commands

    def cmd(self, address, opcode, data="", relay=False):
        """Send ONE read command to ``address`` and return its Reply.

        Raises ForbiddenOpcode before any I/O for anything outside the
        allowlist, CapabilityGap when the controller does not know the command,
        ReadFailed for every other controller error, Unreachable when the
        module cannot be talked to.
        """
        opcode = allowlist.check_allowed(opcode, data)
        data = (data or "").upper()
        address = int(address)
        payload = {"cmd": {"id": address, "c": opcode, "d": data}}
        timeout = HTTP_TIMEOUT_IO_TABLE if opcode == "F9" else HTTP_TIMEOUT
        attempts = 0
        skewed = 0
        retries_left = None
        pauses = ()
        budget_ends = time.monotonic() + COMMAND_BUDGET_SECONDS
        while True:
            attempts += 1
            started = time.monotonic()
            raw = self._post("/sdk/cmd.json", payload, timeout=timeout)
            duration_ms = int((time.monotonic() - started) * 1000)
            body = raw.get("response") if isinstance(raw.get("response"), dict) else raw
            # A reply is only a reply when it names the controller, the command
            # and a status code; anything else ({}, {"error": ...}, another
            # schema) is the module not doing its job, never a silent success.
            if not all(key in body for key in ("id", "c", "e")):
                raise Unreachable(
                    "%s returned a command reply without a status code" % self.host,
                    kind="reply",
                )
            try:
                reply_id = int(body["id"])
                e_code = int(body["e"])
            except (TypeError, ValueError) as exc:
                raise Unreachable(
                    "%s returned a command reply this system cannot read" % self.host,
                    kind="reply",
                ) from exc
            reply_c = str(body["c"] or "").upper()
            reply_data = str(body.get("d") or "").upper()
            is_skewed = reply_id != address or reply_c != opcode
            self._log(
                address,
                opcode,
                data,
                e_code,
                duration_ms,
                reply_data,
                is_skewed,
                attempts,
            )
            if is_skewed:
                skewed += 1
                if skewed > SKEW_RETRIES or time.monotonic() > budget_ends:
                    raise Unreachable(
                        "%s answered for another command %s times in %.0f s (controller %s, %s)"
                        % (
                            self.host,
                            skewed,
                            time.monotonic() - budget_ends + COMMAND_BUDGET_SECONDS,
                            address,
                            opcode,
                        ),
                        kind="skew",
                    )
                self.sleep(SKEW_PAUSE)
                continue
            if e_code == E_OK:
                return Reply(
                    address, opcode, e_code, reply_data, duration_ms, attempts, skewed
                )
            if e_code == E_UNKNOWN_COMMAND or (e_code == E_WRONG_VALUE and relay):
                raise CapabilityGap(opcode, e_code, address)
            policy = RETRY_POLICY.get(e_code)
            if not policy:
                raise ReadFailed(opcode, e_code, address)
            if retries_left is None:
                retries_left, pauses = policy
            if retries_left <= 0 or time.monotonic() > budget_ends:
                # Out of retries, or out of the time one command may take.
                raise ReadFailed(opcode, e_code, address)
            pause = (
                pauses[min(len(pauses) - 1, len(pauses) - retries_left)]
                if pauses
                else 1.0
            )
            retries_left -= 1
            self.sleep(pause)

    def _log(
        self, address, opcode, data, e_code, duration_ms, response_hex, skewed, attempt
    ):
        # The log is the survey's proof of what was sent; a failure to write it
        # is a failure of the survey, so it is allowed to propagate.
        if not self.on_log:
            return
        self.on_log(
            {
                "address": int(address),
                "opcode": opcode,
                "data_sent": data,
                "e_code": e_code,
                "duration_ms": duration_ms,
                "response_hex": response_hex,
                "skewed": bool(skewed),
                "attempt": attempt,
            }
        )


class RealBackend:
    """The production backend: the core's network search and real HTTP.
    Tests substitute FakeBackend."""

    def discovery(self, env):
        return CoreDiscovery(env)

    def client(self, host, port=80, auth=None, on_log=None):
        return HardwareClient(host, port=port, auth=auth, on_log=on_log)

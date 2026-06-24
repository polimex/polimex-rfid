"""Zero-config camera discovery on the local segment.

Three probes, each multicast-first then a unicast /24 sweep fallback, because
multicast (SADP and ONVIF WS-Discovery alike) is subject to IGMP snooping on
managed switches — verified on site: a camera answered a UNICAST probe on the
same port while the switch had stopped forwarding the multicast group to it.

  * SADP  (Hikvision, UDP 37020) — primary for Hikvision: works out-of-box with
    NO ONVIF and NO auth; reports IP/model/serial/MAC/HTTP port/activation.
  * ONVIF WS-Discovery (UDP 3702) — brand-agnostic; only answers when ONVIF is
    enabled on the device.

Parsers are pure/static (unit-tested against canned ProbeMatch payloads); only
the ``discover_*`` methods touch the network. Style mirrors ``camera_api.py``
(stdlib sockets, hardened lxml parsing for untrusted input, sockets closed in
finally, explicit timeouts, ``_logger`` levels per odoo-logger-conventions).
"""
import socket
import time
import uuid
import logging
from xml.etree import ElementTree as ET          # building OUR probes (trusted)

from lxml import etree

from odoo.addons.hr_rfid.models.hr_rfid_webstack import get_local_ip
from odoo.addons.polimex_ip_cam.helpers.safe_xml import parse_untrusted_xml  # untrusted replies

_logger = logging.getLogger(__name__)

# Discovery transports
SADP_GROUP = "239.255.255.250"
SADP_PORT = 37020
WSD_GROUP = "239.255.255.250"
WSD_PORT = 3702

# Per-protocol budgets (seconds). A scan runs SADP + ONVIF, each = multicast
# listen + unicast sweep listen, so keep these small to stay UI-responsive.
MULTICAST_LISTEN = 3
SWEEP_LISTEN = 3
RECV_BUFFER = 65535
MULTICAST_TTL = 2

# Brands as stored on cctv.camera.brand.
BRAND_HIKVISION = "hikvision"
BRAND_ONVIF_GENERIC = "onvif_generic"


class CameraDiscoverer:
    """Discovers IP cameras on the Odoo host's local segment(s).

    Read-only: emits UDP probes and parses replies into normalised records.
    Does NOT authenticate to or reconfigure any device — that is the wizard's
    job once the operator adopts a result.
    """

    def __init__(self, timeout=MULTICAST_LISTEN):
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # Normalised record
    # ------------------------------------------------------------------ #
    @staticmethod
    def _record(ip, brand, model=None, serial=None, mac=None,
                http_port=None, onvif_url=None, activated=None, method=None):
        """One discovered device, keyed to cctv.camera field names where they
        map directly (ip_address/brand/model/serial_number)."""
        return {
            "ip_address": ip,
            "brand": brand,
            "model": model or "",
            "serial_number": serial or "",
            "mac_address": mac or "",
            "http_port": http_port or "",
            "onvif_url": onvif_url or "",
            "activated": activated,
            "discovery_method": method or "",
        }

    # ------------------------------------------------------------------ #
    # Probe builders (our own XML — trusted)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _sadp_probe():
        # Hikvision SADP inquiry — verified against DS-TCG406-E firmware V5.x.
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            "<Probe><Uuid>%s</Uuid><Types>inquiry</Types></Probe>"
            % str(uuid.uuid4()).upper()
        ).encode()

    @staticmethod
    def _wsd_probe():
        # ONVIF WS-Discovery Probe for NetworkVideoTransmitter devices.
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"'
            ' xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
            ' xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"'
            ' xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
            "<e:Header><w:MessageID>uuid:%s</w:MessageID>"
            '<w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
            '<w:Action e:mustUnderstand="true">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>'
            "</e:Header><e:Body><d:Probe>"
            "<d:Types>dn:NetworkVideoTransmitter</d:Types>"
            "</d:Probe></e:Body></e:Envelope>" % uuid.uuid4()
        ).encode()

    # ------------------------------------------------------------------ #
    # Parsers (PURE — no I/O; unit-tested)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _local_text(root, name):
        """Find the first element whose tag (namespace stripped) equals *name*."""
        for el in root.iter():
            if el.tag.rsplit("}", 1)[-1] == name and el.text:
                return el.text.strip()
        return ""

    @classmethod
    def parse_sadp(cls, payload, src_ip=None):
        """Parse a SADP ProbeMatch into a normalised record, or None if the
        payload is not a SADP match. *payload* is bytes or str."""
        try:
            text = payload.decode("utf-8", "replace") if isinstance(payload, bytes) else payload
            root = parse_untrusted_xml(payload)
        except (etree.XMLSyntaxError, ValueError):
            return None
        if cls._local_text(root, "DeviceSN") == "" and cls._local_text(root, "IPv4Address") == "":
            # Parsed as XML but carries neither serial nor address — a
            # misconfigured/foreign responder. Diagnostic only (network noise is
            # expected on a discovery scan), so debug, not warning.
            _logger.debug("SADP-shaped reply without DeviceSN/IPv4Address; skipping")
            return None
        activated = cls._local_text(root, "Activated").lower()
        return cls._record(
            ip=cls._local_text(root, "IPv4Address") or src_ip,
            brand=BRAND_HIKVISION,
            model=cls._local_text(root, "DeviceDescription"),
            serial=cls._local_text(root, "DeviceSN"),
            mac=cls._local_text(root, "MAC"),
            http_port=cls._local_text(root, "HttpPort"),
            activated=(activated == "true") if activated else None,
            method="SADP",
        )

    @classmethod
    def parse_wsd(cls, payload, src_ip=None):
        """Parse an ONVIF WS-Discovery ProbeMatch into a normalised record, or
        None if not a match."""
        try:
            text = payload.decode("utf-8", "replace") if isinstance(payload, bytes) else payload
            root = parse_untrusted_xml(payload)
        except (etree.XMLSyntaxError, ValueError):
            return None
        if "ProbeMatch" not in text:
            return None
        xaddrs = cls._local_text(root, "XAddrs")
        scopes = cls._local_text(root, "Scopes")
        onvif_url = ""
        xaddr_host = ""
        for token in xaddrs.split():
            if token.startswith("http://") and "[" not in token:   # skip IPv6 link-local
                onvif_url = token
                xaddr_host = token.split("//", 1)[1].split("/", 1)[0].split(":", 1)[0]
                break
        # Prefer the packet source IP (where the reply actually arrived from)
        # over the XAddrs host — a hostile device could advertise a spoofed
        # XAddrs to steer the operator at an attacker-chosen address.
        ip = src_ip or xaddr_host
        brand, model = BRAND_ONVIF_GENERIC, ""
        for scope in scopes.split():
            tail = scope.rsplit("/", 1)[-1]
            if "/name/" in scope and tail.lower() == "hikvision":
                brand = BRAND_HIKVISION
            elif "/hardware/" in scope:
                model = tail
        return cls._record(ip=ip, brand=brand, model=model,
                           onvif_url=onvif_url, method="ONVIF")

    # ------------------------------------------------------------------ #
    # Network probes
    # ------------------------------------------------------------------ #
    def _open_socket(self, bind_ip, bind_port, join_group=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((bind_ip if not join_group else "", bind_port))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(bind_ip))
            if join_group:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                socket.inet_aton(join_group) + socket.inet_aton(bind_ip))
            sock.settimeout(1.0)
            return sock
        except OSError:
            # Never leak the fd if bind/setsockopt fails (e.g. port in TIME_WAIT);
            # the caller's except/finally only sees the socket once we return it.
            sock.close()
            raise

    def _collect(self, sock, parse, seen, deadline):
        """Drain replies until *deadline*, parsing each into *seen* keyed by ip."""
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(RECV_BUFFER)
            except socket.timeout:
                continue
            except OSError:
                break
            rec = parse(data, src_ip=addr[0])
            if not rec:
                continue
            ip = rec.get("ip_address")
            if not ip:
                _logger.debug("Discovery reply from %s parsed but had no usable IP; dropped", addr[0])
                continue
            if ip not in seen:
                seen[ip] = rec

    def _discover(self, group, port, probe_bytes, parse):
        """multicast probe + IGMP-proof unicast /24 sweep; returns records."""
        local_ip = get_local_ip()
        if local_ip == "127.0.0.1":
            _logger.warning("Camera discovery: no routable local IP; skipping %s probe", port)
            return []
        subnet = local_ip.rsplit(".", 1)[0]
        seen = {}
        sock = None
        try:
            sock = self._open_socket(local_ip, port, join_group=group)
            for _i in range(3):
                sock.sendto(probe_bytes, (group, port))
            self._collect(sock, parse, seen, time.time() + MULTICAST_LISTEN)
            # Unicast sweep — reliable regardless of switch multicast handling.
            for host in range(1, 255):
                try:
                    sock.sendto(probe_bytes, ("%s.%d" % (subnet, host), port))
                except OSError:
                    pass
            self._collect(sock, parse, seen, time.time() + SWEEP_LISTEN)
        except OSError as e:
            _logger.warning("Camera discovery on UDP %s failed: %s", port, e, exc_info=True)
        finally:
            if sock is not None:
                sock.close()
        return list(seen.values())

    def discover_sadp(self):
        return self._discover(SADP_GROUP, SADP_PORT, self._sadp_probe(), self.parse_sadp)

    def discover_onvif(self):
        return self._discover(WSD_GROUP, WSD_PORT, self._wsd_probe(), self.parse_wsd)

    def discover(self):
        """Run every transport and merge by IP (a device seen by SADP and ONVIF
        is one record). SADP is probed FIRST so its richer identity — Hikvision
        brand, serial, activation — wins the merge over the ONVIF reply (whose
        brand may only be the generic fallback); ONVIF then just enriches the
        onvif_url."""
        _logger.info("Starting camera discovery (SADP + ONVIF) on the local segment")
        merged = {}
        for rec in self.discover_sadp() + self.discover_onvif():
            ip = rec["ip_address"]
            existing = merged.get(ip)
            if existing is None:
                merged[ip] = rec
            else:
                # enrich: keep non-empty fields, append discovery method
                for key, val in rec.items():
                    if val and not existing.get(key):
                        existing[key] = val
                methods = {existing["discovery_method"], rec["discovery_method"]}
                existing["discovery_method"] = ", ".join(sorted(m for m in methods if m))
        _logger.info("Camera discovery found %s device(s) on the local segment", len(merged))
        return list(merged.values())

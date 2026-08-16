"""Zero-config camera discovery wizard.

Mirrors the canonical Polimex scan-and-adopt pattern
(hr_rfid.hr_rfid_webstack_discovery): a TransientModel whose One2many is
populated at open by a discovery probe, the operator drops unwanted rows, then
one action creates the real cctv.camera records.

The network probe is isolated in helpers/ipcam_discovery.CameraDiscoverer.
A context key ``ipcam_discovery_results`` (a list of normalised record dicts)
short-circuits the socket probe — the deterministic seam used by tests and the
UI tour so they never depend on real cameras being on the wire.
"""
from odoo import api, fields, models, _

from odoo.addons.polimex_ip_cam.helpers.ipcam_discovery import CameraDiscoverer

import logging

_logger = logging.getLogger(__name__)


class CctvCameraDiscoveryLine(models.TransientModel):
    _name = "cctv.camera.discovery.line"
    _description = "Discovered Camera"

    discovery_id = fields.Many2one(
        comodel_name="cctv.camera.discovery",
        ondelete="cascade",
        readonly=True,
        help="Discovery run that found this camera.",
    )
    name = fields.Char(
        string="Camera Name",
        help="Name the camera will be created with. Pre-filled from the model "
             "and address; edit it to something meaningful before adopting.",
    )
    ip_address = fields.Char(readonly=True, help="Address the camera reported on the local segment.")
    brand = fields.Selection(
        selection=[("hikvision", "Hikvision"), ("dahua", "Dahua"), ("onvif_generic", "ONVIF (generic)")],
        readonly=True,
        help="Detected from the discovery reply (SADP/ONVIF). Generic ONVIF for non-Hikvision devices.",
    )
    model = fields.Char(readonly=True, help="Hardware model as reported by the device.")
    serial_number = fields.Char(readonly=True, help="Device serial number from the discovery reply.")
    mac_address = fields.Char(readonly=True, help="Hardware (MAC) address — stable identity across DHCP changes.")
    http_port = fields.Char(readonly=True, help="HTTP/ISAPI port the device serves on (default 80).")
    discovery_method = fields.Char(readonly=True, help="Which probe found it: SADP, ONVIF, or both.")
    existing_camera_id = fields.Many2one(
        comodel_name='cctv.camera', readonly=True,
        help="The camera record this device already is, recognised by its "
             "serial number (or, failing that, its address). Filled in by "
             "the scan; such a device will not be added a second time.",
    )
    status = fields.Selection(
        [('new', "New"), ('known', "Already added")], readonly=True,
        default='new',
        help="Whether this device is already registered here. The scan "
             "recognises registered cameras by serial number, so the list "
             "doubles as a check that they are alive on the network.",
    )
    activated = fields.Boolean(
        readonly=True,
        help="Hikvision cameras must be activated (password set) before use. "
             "Unchecked devices are still factory-default and need activation first.",
    )


class CctvCameraDiscovery(models.TransientModel):
    _name = "cctv.camera.discovery"
    _description = "Camera Discovery"

    def _discover(self):
        """Populate the result lines. Uses the injected context results when
        present (tests/tour), otherwise probes the local segment.

        Devices already registered here are SHOWN, labelled with the record
        they are - not silently dropped. Dropping them left the operator in
        front of a list of serial numbers with no way to tell which cameras
        of the site are covered and which are not (the owner, verbatim: "от
        тази джунгла с цифри и букви как да разбера кои камери вече сме
        добавили"); shown and named, the scan doubles as a liveness check of
        the registered park. Only the NEW lines are candidates for adding.
        """
        injected = self.env.context.get("ipcam_discovery_results")
        records = injected if injected is not None else CameraDiscoverer().discover()

        # One search; the cctv.camera record rule scopes it to the user's allowed
        # companies, so the matching below is correctly per-company (a device
        # registered in another company is offered for adoption here).
        camera_env = self.env["cctv.camera"]
        existing = camera_env.search([])
        by_serial = {c.serial_number: c for c in existing if c.serial_number}
        by_ip = {c.ip_address: c for c in existing if c.ip_address}

        # Create real transient line records and return their ids (the canonical
        # scan-wizard pattern, mirroring hr.rfid.webstack.discovery). Returning
        # (0,0,{...}) command tuples instead would lose the readonly field values
        # on form save — the web client does not echo readonly fields back, so the
        # adopted line would have an empty ip_address/serial.
        line_env = self.env["cctv.camera.discovery.line"]
        line_ids = []
        for rec in records:
            serial = (rec.get("serial_number") or "").strip()
            ip = (rec.get("ip_address") or "").strip()
            # The serial is the identity; the address is only a last resort
            # for devices that reported no serial at all.
            known = by_serial.get(serial) or (not serial and by_ip.get(ip)) or False
            model = (rec.get("model") or "").strip()
            line = line_env.create({
                "name": (known and known.name)
                        or ("%s %s" % (model, ip)).strip() or ip or _("New Camera"),
                "ip_address": ip,
                "brand": rec.get("brand") or "onvif_generic",
                "model": model,
                "serial_number": serial,
                "mac_address": (rec.get("mac_address") or "").strip(),
                "http_port": (rec.get("http_port") or "").strip(),
                "discovery_method": (rec.get("discovery_method") or "").strip(),
                "activated": bool(rec.get("activated")),
                "existing_camera_id": known and known.id,
                "status": 'known' if known else 'new',
            })
            line_ids.append(line.id)
        return line_ids

    found_camera_ids = fields.One2many(
        comodel_name="cctv.camera.discovery.line",
        inverse_name="discovery_id",
        string="Discovered Cameras",
        default=_discover,
        help="Cameras found on the local network. Remove the ones you do not "
             "want, then click Add Cameras.",
    )

    def action_create_cameras(self):
        """Create a cctv.camera per remaining line, then open the camera list
        filtered to what was just added. Connection details (sub-serial,
        firmware) are filled later by Check Connection."""
        self.ensure_one()
        camera_env = self.env["cctv.camera"]
        created = camera_env
        skipped = 0
        for line in self.found_camera_ids:
            if line.existing_camera_id:
                # Shown for orientation ("this one you already have"), never
                # added a second time - the serial is the identity.
                continue
            if not line.ip_address:
                # Only reachable if the operator cleared the address; never
                # adopt an unusable camera, but make the drop visible.
                skipped += 1
                continue
            vals = {
                "name": line.name or line.ip_address,
                "ip_address": line.ip_address,
                "brand": line.brand,                       # always set by _discover
                "company_id": self.env.company.id,         # adopt into the active company
            }
            if line.model:
                vals["model"] = line.model
            if line.serial_number:
                vals["serial_number"] = line.serial_number
            if line.http_port and line.http_port.isdigit() and 0 < int(line.http_port) <= 65535:
                vals["port"] = int(line.http_port)
            elif line.http_port:
                _logger.warning(
                    "Discovered camera %s reported an unusable HTTP port %r; "
                    "creating it on the default port instead",
                    line.ip_address, line.http_port)
            created += camera_env.create(vals)

        if skipped:
            _logger.warning(
                "Skipped %s discovery line(s) with no IP address during adoption", skipped)

        if not created:
            return {"type": "ir.actions.act_window_close"}

        _logger.info("Adopted %s camera(s) from network discovery", len(created))
        action = self.env["ir.actions.actions"]._for_xml_id("polimex_ip_cam.action_cctv_camera")
        action.update({
            "domain": [("id", "in", created.ids)],
            "context": {},
        })
        return action

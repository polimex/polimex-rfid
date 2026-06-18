from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_access")
class TestAnprAccessDecision(TransactionCase):
    """granted/denied for a recognised plate is decided from THIS camera's
    plate lists in Odoo (cctv.camera.rfid.rel), NOT from the camera's
    barrierGateCtrlType field.

    Confirmed live on DS-TCG406-E V5.4.4: the push for a whitelisted plate
    carries barrierGateCtrlType='0' and an empty listType, so the old
    'granted iff barrierGateCtrlType == 1' rule booked every recognised plate
    as denied access."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.plate_type = cls.env.ref("hr_rfid.hr_rfid_card_type_8")
        cls.cam = cls.env["cctv.camera"].create({
            "name": "Access Cam", "company_id": cls.company.id,
            "ip_address": "10.0.0.50", "port": 80, "username": "admin",
            "password": "x", "tz": "Europe/Sofia",
        })

    def _files(self, plate, barrier="0"):
        # Mirrors the real DS-TCG406-E V5.4.4 push for a recognised plate:
        # barrierGateCtrlType '0' (camera does not drive the barrier) and no
        # listType in the payload.
        return {"anpr": {
            "ANPR": {
                "licensePlate": plate, "direction": "forward",
                "detectDir": "8", "detectType": "2",
                "barrierGateCtrlType": barrier, "confidenceLevel": "98",
            },
            "dateTime": "2027-01-01T10:00:00+02:00",
            "eventType": "ANPR", "ipAddress": "192.168.74.79",
            "macAddress": "aa:bb", "activePostCount": "1", "eventState": "active",
            "carDirectionType": "0",
        }}

    def _card(self, plate):
        partner = self.env["res.partner"].create({"name": "H %s" % plate})
        return self.env["hr.rfid.card"].create({
            "number": plate, "card_type": self.plate_type.id,
            "contact_id": partner.id, "company_id": self.company.id,
        })

    def _rel(self, card, category):
        return self.env["cctv.camera.rfid.rel"].create({
            "camera_id": self.cam.id, "card_id": card.id,
            "list_category": category,
        })

    def _last_user_event(self, plate):
        return self.env["hr.rfid.event.user"].search(
            [("camera_id", "=", self.cam.id), ("license_plate", "=", plate)],
            order="id desc", limit=1)

    def test_whitelist_plate_is_granted(self):
        # The regression: barrierGateCtrlType='0' for a whitelisted plate.
        card = self._card("PB8141KC")
        self._rel(card, "whitelist")
        self.cam.parse_event(self._files("PB8141KC"))
        ev = self._last_user_event("PB8141KC")
        self.assertTrue(ev)
        self.assertEqual(ev.event_action, "1",
                         "whitelisted plate must be granted access ('1') even "
                         "though barrierGateCtrlType is '0'")

    def test_blacklist_plate_is_denied(self):
        card = self._card("PB9999XX")
        self._rel(card, "blacklist")
        self.cam.parse_event(self._files("PB9999XX"))
        ev = self._last_user_event("PB9999XX")
        self.assertTrue(ev)
        self.assertEqual(ev.event_action, "2", "blacklisted plate must be denied")

    def test_known_card_without_relation_is_denied(self):
        # Owner is known (card exists) but the plate is not on THIS camera's
        # list -> denied, not granted.
        self._card("PB1234AB")
        self.cam.parse_event(self._files("PB1234AB"))
        ev = self._last_user_event("PB1234AB")
        self.assertTrue(ev)
        self.assertEqual(ev.event_action, "2",
                         "a plate with no relation for this camera is denied")

    def test_blacklist_wins_over_whitelist_conflict(self):
        # No unique constraint on (camera, card): a card can carry both a
        # whitelist and a blacklist relation. Fail safe — deny.
        card = self._card("PB6666DE")
        self._rel(card, "whitelist")
        self._rel(card, "blacklist")
        self.cam.parse_event(self._files("PB6666DE"))
        ev = self._last_user_event("PB6666DE")
        self.assertTrue(ev)
        self.assertEqual(ev.event_action, "2",
                         "a blacklist relation must deny even when a whitelist "
                         "relation also exists (fail safe)")

    def test_barrier_ctrl_type_does_not_override_blacklist(self):
        # Even if the camera reports barrierGateCtrlType='1', a blacklisted
        # plate stays denied — the Odoo list is authoritative.
        card = self._card("PB5555CD")
        self._rel(card, "blacklist")
        self.cam.parse_event(self._files("PB5555CD", barrier="1"))
        ev = self._last_user_event("PB5555CD")
        self.assertTrue(ev)
        self.assertEqual(ev.event_action, "2",
                         "barrierGateCtrlType must not override the Odoo list")

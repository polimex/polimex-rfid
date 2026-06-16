from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.models.cctv_camera_rfid_rel import LIST_TYPE_MAP


@tagged("post_install", "-at_install", "polimex_ip_cam")
class TestListCategoryTwoBuckets(TransactionCase):
    """The list category was simplified from five buckets to the two the
    camera hardware supports: whitelist (allow) and blacklist (deny)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.plate_type = cls.env.ref("hr_rfid.hr_rfid_card_type_8")
        cls.camera = cls.env["cctv.camera"].create({
            "name": "Gate Cam",
            "company_id": cls.company.id,
            "ip_address": "10.0.0.20",
            "port": 80,
            "username": "admin",
            "password": "x",
            "tz": "Europe/Sofia",
        })

    def _make_plate_rel(self, plate, category):
        partner = self.env["res.partner"].create({"name": "Holder %s" % plate})
        card = self.env["hr.rfid.card"].create({
            "number": plate,
            "card_type": self.plate_type.id,
            "contact_id": partner.id,
            "company_id": self.company.id,
        })
        return self.env["cctv.camera.rfid.rel"].create({
            "camera_id": self.camera.id,
            "card_id": card.id,
            "list_category": category,
        })

    def test_selection_has_exactly_two_values(self):
        selection = dict(
            self.env["cctv.camera.rfid.rel"]._fields["list_category"].selection
        )
        self.assertEqual(
            set(selection), {"whitelist", "blacklist"},
            "list_category must offer exactly whitelist and blacklist",
        )

    def test_default_is_whitelist(self):
        default = self.env["cctv.camera.rfid.rel"].default_get(
            ["list_category"]
        ).get("list_category")
        self.assertEqual(default, "whitelist")

    def test_compute_list_counts(self):
        self._make_plate_rel("CA1111AA", "whitelist")
        self._make_plate_rel("CA2222BB", "whitelist")
        self._make_plate_rel("CA3333CC", "blacklist")
        self.camera.invalidate_recordset(
            ["rfid_whitelist_count", "rfid_blacklist_count"]
        )
        self.assertEqual(self.camera.rfid_whitelist_count, 2)
        self.assertEqual(self.camera.rfid_blacklist_count, 1)

    def test_list_type_mapping_is_zero_one(self):
        self.assertEqual(LIST_TYPE_MAP["whitelist"], "0")
        self.assertEqual(LIST_TYPE_MAP["blacklist"], "1")
        self.assertEqual(
            set(LIST_TYPE_MAP), {"whitelist", "blacklist"},
            "Only the two hardware-supported buckets may be mapped",
        )

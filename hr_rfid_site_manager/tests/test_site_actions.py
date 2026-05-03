from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "rfid_site_manager")
class TestSiteActions(common.TransactionCase):
    """Backend coverage for hr.rfid.site action helpers used by the
    site_chart OWL widget.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Site = cls.env["hr.rfid.site"]
        cls.root = Site.create({"name": "HQ"})
        cls.floor1 = Site.create({"name": "Floor 1", "parent_id": cls.root.id})
        cls.floor2 = Site.create({"name": "Floor 2", "parent_id": cls.root.id})
        cls.subroom = Site.create({"name": "Server Room", "parent_id": cls.floor1.id})

    def test_get_site_hierarchy_root(self):
        h = self.root.get_site_hierarchy()
        self.assertFalse(h["parent"], "Root site should report no parent")
        self.assertEqual(h["self"]["id"], self.root.id)
        self.assertEqual(h["self"]["name"], "HQ")
        children_ids = {c["id"] for c in h["children"]}
        self.assertEqual(children_ids, {self.floor1.id, self.floor2.id})

    def test_get_site_hierarchy_middle_node(self):
        h = self.floor1.get_site_hierarchy()
        self.assertEqual(h["parent"]["id"], self.root.id)
        self.assertEqual(h["self"]["id"], self.floor1.id)
        self.assertEqual([c["id"] for c in h["children"]], [self.subroom.id])

    def test_get_site_hierarchy_leaf(self):
        h = self.subroom.get_site_hierarchy()
        self.assertEqual(h["parent"]["id"], self.floor1.id)
        self.assertEqual(h["self"]["id"], self.subroom.id)
        self.assertEqual(h["children"], [])

    def test_get_site_hierarchy_empty_recordset(self):
        empty = self.env["hr.rfid.site"]
        self.assertEqual(empty.get_site_hierarchy(), {})

    def test_open_child_site_list_action_returns_filtered_domain(self):
        action = self.root.open_child_site_list_action()
        self.assertEqual(action["res_model"], "hr.rfid.site")
        self.assertIn(("parent_id", "=", self.root.id), action["domain"])

    def test_open_door_list_action_uses_child_of(self):
        """The door action must use child_of so doors of subsites are included."""
        action = self.floor1.open_door_list_action()
        self.assertEqual(action["res_model"], "hr.rfid.door")
        self.assertIn(("site_id", "child_of", self.floor1.id), action["domain"])

    def test_open_controller_list_action_uses_child_of(self):
        action = self.root.open_controller_list_action()
        self.assertIn(("site_id", "child_of", self.root.id), action["domain"])

    def test_open_webstack_list_action_uses_child_of(self):
        action = self.root.open_webstack_list_action()
        self.assertIn(("site_id", "child_of", self.root.id), action["domain"])

    def test_open_access_group_list_action_uses_child_of(self):
        action = self.root.open_access_group_list_action()
        self.assertIn(("site_id", "child_of", self.root.id), action["domain"])

    def test_open_alarm_line_group_list_action_uses_child_of(self):
        action = self.root.open_alarm_line_group_list_action()
        self.assertIn(("site_id", "child_of", self.root.id), action["domain"])

    def test_open_actions_require_single_record(self):
        """All open_* helpers call ensure_one(). Multi-record call must raise."""
        with self.assertRaises(ValueError):
            (self.root | self.floor1).open_door_list_action()

    def test_get_children_site_ids_includes_self_and_descendants(self):
        descendants = self.root.get_children_site_ids()
        self.assertIn(self.root, descendants)
        self.assertIn(self.floor1, descendants)
        self.assertIn(self.floor2, descendants)
        self.assertIn(self.subroom, descendants)

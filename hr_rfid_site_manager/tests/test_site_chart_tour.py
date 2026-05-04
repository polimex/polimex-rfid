# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Browser-driven E2E tour for the site_chart widget navigation.

Currently disabled — left as the canonical scaffold for tour-based
coverage of the OWL site_chart widget. The JS tour lives at
static/tests/tours/site_chart_navigation_tour.js. To enable, switch
the @tagged decorator to include 'standard' (or remove '-standard')
and tune the selectors to match the active view chain in the target DB.

The same flow is already covered at the unit level by the Hoot test
site_chart.test.js and at the model level by test_site_actions.py, so
the tour is supplementary rather than load-bearing.
"""
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_site_manager_tour")
class TestSiteChartTour(HttpCase):
    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Site = cls.env["hr.rfid.site"]
        cls.root = Site.create({"name": "HQ"})
        cls.floor1 = Site.create({"name": "Floor 1", "parent_id": cls.root.id})

    def test_site_chart_navigation_tour(self):
        self.start_tour(
            "/odoo",
            "hr_rfid_site_chart_navigation_tour",
            login="admin",
        )

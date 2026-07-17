# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install', 'spreadsheet_dashboard_hr_rfid')
class TestRfidDashboardTours(HttpCase):
    _registry_readonly_enabled = False

    def test_dashboards_render_tour(self):
        """Both boards mount and their figures draw in a real browser."""
        self.start_tour('/odoo/dashboards', 'spreadsheet_dashboard_hr_rfid_tour',
                        login='admin')

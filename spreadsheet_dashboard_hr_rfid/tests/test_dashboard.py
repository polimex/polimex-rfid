# -*- coding: utf-8 -*-
"""Structural + data tests for the Access Control / Security dashboards.

The o-spreadsheet renderer is client-side, so these tests guard everything the
server CAN prove: the dashboard records and their documents are well-formed,
every pivot/chart aggregation actually executes on the ORM, the read-only
serialization works, and the click-through targets (the User/System Events
lists, which open with a "today" default filter) are not empty when today has
events - the regression behind "clicks open empty lists".
"""
import base64
import json
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

DASHBOARDS = (
    'spreadsheet_dashboard_hr_rfid.spreadsheet_dashboard_access_control',
    'spreadsheet_dashboard_hr_rfid.spreadsheet_dashboard_security_devices',
)


@tagged('post_install', '-at_install', 'spreadsheet_dashboard_hr_rfid')
class TestRfidDashboards(TransactionCase):

    def _docs(self):
        for xmlid in DASHBOARDS:
            dash = self.env.ref(xmlid)
            yield dash, json.loads(base64.b64decode(dash.spreadsheet_binary_data))

    def test_records_registered(self):
        for xmlid in DASHBOARDS:
            dash = self.env.ref(xmlid)
            self.assertTrue(dash.is_published)
            self.assertEqual(dash.dashboard_group_id,
                             self.env.ref('spreadsheet_dashboard.spreadsheet_dashboard_group_hr'))
            self.assertIn(self.env.ref('hr_rfid.hr_rfid_group_officer'), dash.group_ids)

    def test_documents_wellformed(self):
        """Filters wired, pivots sliceable, figures inside the grid."""
        for dash, doc in self._docs():
            filter_ids = {f['id'] for f in doc['globalFilters']}
            self.assertTrue(filter_ids, dash.name)
            for pid, pivot in doc['pivots'].items():
                for fid in pivot.get('fieldMatching', {}):
                    self.assertIn(fid, filter_ids,
                                  f'{dash.name}: pivot {pid} matched to unknown filter')
            sheet = doc['sheets'][0]
            grid_w = sum(c['size'] for c in sheet['cols'].values())
            max_right = max(f['offset']['x'] + f['width'] for f in sheet['figures'])
            self.assertGreaterEqual(grid_w, max_right,
                                    f'{dash.name}: figures would clip outside the grid')
            # every scorecard/gauge cell reference resolves
            cells = {name: sh for sh in doc['sheets'] for name in sh['cells']}
            for sh in doc['sheets']:
                for fig in sh['figures']:
                    ref = fig['data'].get('keyValue') or fig['data'].get('dataRange')
                    if ref:
                        cell = ref.split('!')[1].replace('$', '')
                        self.assertIn(cell, cells, f'{dash.name}: dangling ref {ref}')

    def test_aggregations_execute(self):
        """Every pivot and odoo-chart read_group runs on the real ORM."""
        for dash, doc in self._docs():
            for pid, pivot in doc['pivots'].items():
                gbs = [r['fieldName'] + (':' + r['granularity'] if r.get('granularity') else '')
                       for r in pivot.get('rows', [])]
                aggs = [f"{m['fieldName']}:{'sum' if m.get('aggregator') in (None, 'sum_currency') else m['aggregator']}"
                        for m in pivot['measures'] if m['fieldName'] != '__count']
                self.env[pivot['model']].read_group(pivot['domain'], aggs, gbs, lazy=False)
            for sh in doc['sheets']:
                for fig in sh['figures']:
                    data = fig['data']
                    if not data.get('type', '').startswith('odoo_'):
                        continue
                    meta = data['metaData']
                    aggs = [] if meta['measure'] == '__count' else [f"{meta['measure']}:sum"]
                    self.env[meta['resModel']].read_group(
                        data['searchParams']['domain'], aggs, meta.get('groupBy', []), lazy=False)

    def test_readonly_serialization(self):
        for dash, _doc in self._docs():
            dash._get_serialized_readonly_dashboard()

    def test_click_through_today_not_empty(self):
        """The events lists open with a 'today' filter; with today's data they
        must not be empty (dashboard clicks used to land on blank lists)."""
        company = self.env.ref('base.main_company')
        webstack = self.env['hr.rfid.webstack'].create({
            'name': 'T-WS', 'serial': '990001', 'key': '1234',
            'hw_version': '100.1', 'version': '1.44', 'active': True,
            'tz': 'Europe/Sofia', 'company_id': company.id})
        ctrl = self.env['hr.rfid.ctrl'].create({
            'name': 'T-CTRL', 'ctrl_id': 9, 'serial_number': '9901',
            'webstack_id': webstack.id, 'hw_version': '9', 'sw_version': '740',
            'max_cards_count': 100, 'max_events_count': 100, 'readers': 2,
            'mode': 2, 'inputs': 0, 'outputs': 0, 'input_states': 0,
            'output_states': 0, 'alarm_lines': 0, 'io_table_lines': 0, 'io_table': ''})
        door = self.env['hr.rfid.door'].create({
            'name': 'T-Door', 'number': 1, 'controller_id': ctrl.id,
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_def').id})
        reader = self.env['hr.rfid.reader'].create({
            'name': 'T-R1', 'number': 1, 'reader_type': '0', 'mode': '01',
            'controller_id': ctrl.id, 'door_id': door.id})
        employee = self.env['hr.employee'].create({'name': 'T Emp', 'company_id': company.id})
        now = fields.Datetime.now()
        self.env['hr.rfid.event.user'].create({
            'event_action': '1', 'event_time': now - timedelta(minutes=5),
            'door_id': door.id, 'reader_id': reader.id, 'ctrl_addr': 9,
            'employee_id': employee.id})
        self.env['hr.rfid.event.system'].create({
            'name': 'T sys', 'event_action': '25',
            'timestamp': now - timedelta(minutes=5),
            'door_id': door.id, 'controller_id': ctrl.id, 'webstack_id': webstack.id})

        today_domain = [('event_time', '>=', datetime.combine(now.date(), datetime.min.time()))]
        self.assertGreater(self.env['hr.rfid.event.user'].search_count(today_domain), 0,
                           "User Events 'today' click-through target is empty")
        sys_domain = [('timestamp', '>=', datetime.combine(now.date(), datetime.min.time()))]
        self.assertGreater(self.env['hr.rfid.event.system'].search_count(sys_domain), 0,
                           "System Events 'today' click-through target is empty")

    def test_demo_generators_cover_today(self):
        """The shipped demo generators must include TODAY, so a fresh demo DB's
        dashboard click-throughs (today-filtered lists) are never empty."""
        param = self.env['ir.config_parameter'].sudo()
        if not param.get_param('hr_rfid.demo_events_generated'):
            self.skipTest('demo data not loaded')
        today_start = datetime.combine(fields.Date.today(), datetime.min.time())
        self.assertGreater(
            self.env['hr.rfid.event.user'].search_count([('event_time', '>=', today_start)]), 0)

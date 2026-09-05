"""Narrative 1 (start) and 2: finding the modules, on the LAN and behind a router.

Owner: "Първо се прави автоматична детекция на модули и се дава списъкът им с
възможност да се добавят IP-та на модули, които не са намерени".
"""
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import HwImportCase, MODULE_A_IP, MODULE_A_SERIAL, MODULE_B_IP, MODULE_B_SERIAL


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_discovery')
class TestDiscovery(HwImportCase):

    def test_the_network_search_lists_the_modules_it_hears(self):
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self.assertEqual(run.state, 'draft')
        module = run.module_ids
        self.assertEqual(len(module), 1)
        self.assertEqual(module.ip, MODULE_A_IP)
        self.assertEqual(module.serial, MODULE_A_SERIAL)
        self.assertEqual(module.status, 'new')
        self.assertEqual(module.dev_found, 5)
        self.assertIn('old-server.example', module.server_url)
        self.assertTrue(module.include)
        self.assertNotIn('secret', module.config_json, "keys and passwords never land in the survey")

    def test_a_module_behind_a_router_is_added_by_address(self):
        run = self._new_run()
        module = self._add_module_b(run)
        self.assertEqual(module.source, 'manual')
        self.assertEqual(module.serial, MODULE_B_SERIAL)
        self.assertEqual(module.hw_version, '10.3')
        self.assertEqual(module.status, 'new')
        self.assertEqual(module.dev_found, 2)

    def test_an_address_that_does_not_answer_stays_listed_as_unreachable(self):
        run = self._new_run()
        wiz = self.env['hr.rfid.hw.import.add.ip.wiz'].create({'run_id': run.id, 'ip': '192.0.2.99'})
        result = wiz.action_add()
        module = run.module_ids
        self.assertEqual(module.status, 'unreachable')
        self.assertEqual(result['params']['type'], 'warning')
        with self.assertRaises(UserError):
            run.action_read()

    def test_a_module_already_registered_here_is_shown_and_left_out_by_default(self):
        self.env['hr.rfid.webstack'].sudo().create({
            'name': 'Existing module', 'serial': MODULE_A_SERIAL, 'active': False,
            'company_id': self.company.id})
        run = self._new_run()
        run.action_discover()
        self._work(run)
        module = run.module_ids
        self.assertEqual(module.status, 'known')
        self.assertFalse(module.include)
        self.assertTrue(module.existing_webstack_id)

    def test_the_same_address_cannot_be_added_twice(self):
        """The operator who types an address that is already listed gets told
        so, and is pointed at 'Check again' on that row - never a database error."""
        run = self._new_run()
        self._add_module_b(run)
        with self.assertRaises(UserError) as caught:
            self._add_module_b(run)
        self.assertIn(MODULE_B_IP, str(caught.exception))
        self.assertEqual(len(run.module_ids), 1)

    def test_discovery_sends_no_controller_command(self):
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self._add_module_b(run)
        self.assertEqual(self.backend.commands_sent(), [])
        self.assertFalse(run.cmd_log_ids)

import json

from odoo.tests import HttpCase, tagged

URL = '/hr/rfid/terminal/lookup'


@tagged('post_install', '-at_install', 'terminal_lookup')
class TestTerminalLookup(HttpCase):
    """Narrative: a terminal next to a controller resolves a swiped card to
    the employee's name, and cannot be used to enumerate the card base."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        # NOTE: hr.rfid.webstack.key is related to endpoint_id.key and is 4 chars
        # wide (the firmware credential format) - a longer key silently truncates.
        cls.webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'Terminal test module',
            'serial': '999001',
            'key': 'A1B2',
            'company_id': cls.company.id,
            'available': 'a',
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Иван Петров',
            'company_id': cls.company.id,
        })
        cls.card = cls.env['hr.rfid.card'].create({
            'number': '0012345678',
            'employee_id': cls.employee.id,
            'company_id': cls.company.id,
        })

    def _call(self, payload):
        response = self.url_open(
            URL, data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
        )
        return response.status_code, response.json()

    def test_known_card_returns_employee(self):
        code, body = self._call({
            'convertor': '999001', 'key': 'A1B2', 'card': '0012345678',
        })
        self.assertEqual(code, 200)
        self.assertTrue(body["found"], msg=str(body))
        self.assertEqual(body['name'], 'Иван Петров')
        self.assertEqual(body['employee_id'], self.employee.id)

    def test_unknown_card_is_not_an_error(self):
        code, body = self._call({
            'convertor': '999001', 'key': 'A1B2', 'card': '0099999999',
        })
        self.assertEqual(code, 200)
        self.assertFalse(body['found'])
        self.assertNotIn('error', body)

    def test_wrong_key_is_rejected(self):
        _, body = self._call({
            'convertor': '999001', 'key': 'wrong', 'card': '0012345678',
        })
        self.assertFalse(body['found'])
        self.assertEqual(body['error'], 'unauthorized')

    def test_unknown_serial_is_rejected(self):
        _, body = self._call({
            'convertor': '000000', 'key': 'A1B2', 'card': '0012345678',
        })
        self.assertFalse(body['found'])
        self.assertEqual(body['error'], 'unauthorized')

    def test_missing_parameters(self):
        _, body = self._call({'convertor': '999001', 'key': 'A1B2'})
        self.assertFalse(body['found'])
        self.assertEqual(body['error'], 'missing_parameters')

    def test_rate_limit_kicks_in(self):
        payload = {'convertor': '999002', 'key': 'x', 'card': '0012345678'}
        limited = False
        for _ in range(25):
            _, body = self._call(payload)
            if body.get('error') == 'rate_limited':
                limited = True
                break
        self.assertTrue(limited, 'the lookup budget must stop a probing caller')

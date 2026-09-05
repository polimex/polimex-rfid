"""The client survives what a passive gateway does: stray replies and silence."""
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_hardware_import.helpers import transport
from odoo.addons.hr_rfid_hardware_import.helpers.fake_transport import FakeBackend


class _Response:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not JSON")
        return self._payload


class _Session:
    """A requests session whose answers are scripted per call; an answer given
    as (status, payload) sets the HTTP status."""

    def __init__(self, answers, get_answer=None):
        self.answers = list(answers)
        self.posted = []
        self.get_answer = get_answer if get_answer is not None else {'convertor': 'X'}

    @staticmethod
    def _response(answer):
        if isinstance(answer, tuple):
            return _Response(answer[1], status=answer[0])
        return _Response(answer)

    def post(self, url, json=None, auth=None, timeout=None, **kwargs):
        self.posted.append(json)
        return self._response(self.answers.pop(0))

    def get(self, url, params=None, auth=None, timeout=None, **kwargs):
        return self._response(self.get_answer)


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_transport')
class TestTransport(TransactionCase):

    def _client(self, answers, log=None):
        session = _Session(answers)
        client = transport.HardwareClient('192.0.2.1', on_log=(log.append if log is not None else None),
                                          sleep=lambda s: None, session=session)
        return client, session

    def test_a_reply_for_another_command_is_discarded_and_the_command_repeated(self):
        log = []
        client, session = self._client([
            {'id': 15, 'c': 'B3', 'e': 0, 'd': 'AA'},
            {'id': 15, 'c': 'F0', 'e': 0, 'd': 'BB'},
        ], log)
        reply = client.cmd(15, 'F0')
        self.assertEqual(reply.data, 'BB')
        self.assertEqual(reply.skewed, 1)
        self.assertEqual(len(session.posted), 2)
        self.assertTrue(log[0]['skewed'])
        self.assertFalse(log[1]['skewed'])

    def test_no_response_is_retried_then_reported(self):
        client, session = self._client([{'id': 15, 'c': 'F0', 'e': 20, 'd': ''}] * 4)
        with self.assertRaises(transport.ReadFailed) as caught:
            client.cmd(15, 'F0')
        self.assertEqual(caught.exception.e_code, 20)
        self.assertEqual(len(session.posted), 4)

    def test_an_unknown_command_is_a_gap_not_a_failure(self):
        client, session = self._client([{'id': 15, 'c': 'B0', 'e': 14, 'd': ''}])
        with self.assertRaises(transport.CapabilityGap):
            client.cmd(15, 'B0', '01')
        self.assertEqual(len(session.posted), 1)

    def test_wrong_value_is_a_gap_only_on_relay_controllers(self):
        client, _ = self._client([{'id': 34, 'c': 'F3', 'e': 4, 'd': ''}])
        with self.assertRaises(transport.CapabilityGap):
            client.cmd(34, 'F3', '01', relay=True)
        client, _ = self._client([{'id': 15, 'c': 'F3', 'e': 4, 'd': ''}])
        with self.assertRaises(transport.ReadFailed):
            client.cmd(15, 'F3', '01')

    def test_the_wrapped_reply_shape_is_accepted_too(self):
        client, _ = self._client([{'response': {'id': 15, 'c': 'F0', 'e': 0, 'd': 'CC'}}])
        self.assertEqual(client.cmd(15, 'F0').data, 'CC')

    def test_a_reply_without_a_status_code_is_not_a_success(self):
        """{} or {"error": ...} from the module is the module failing, never an
        empty setting that reads as 'nothing configured'."""
        for answer in ({}, {'error': 'busy'}, {'response': {}}, {'id': 15, 'c': 'F0'},
                       {'id': 'x', 'c': 'F0', 'e': 0}):
            client, _ = self._client([answer])
            with self.assertRaises(transport.Unreachable, msg=repr(answer)):
                client.cmd(15, 'F0')

    def test_an_answer_that_is_not_a_json_object_is_unreachable(self):
        for payload in ([1, 2], 'null', 'not json at all'):
            client, _ = self._client([payload])
            with self.assertRaises(transport.Unreachable, msg=repr(payload)):
                client.cmd(15, 'F0')
        client, _ = self._client([])
        client.session.get_answer = [1, 2]
        with self.assertRaises(transport.Unreachable):
            client.get_config()

    def test_a_password_problem_is_named_as_such(self):
        client, _ = self._client([(401, {})])
        with self.assertRaises(transport.Unreachable) as caught:
            client.cmd(15, 'F0')
        self.assertIn('password', str(caught.exception))
        self.assertEqual(caught.exception.status, 401)
        client, _ = self._client([(404, {})])
        with self.assertRaises(transport.Unreachable) as caught:
            client.cmd(15, 'F0')
        self.assertEqual(caught.exception.status, 404)

    def test_a_command_log_that_cannot_be_written_stops_the_read(self):
        """The log is the survey's proof; a read without its proof is not kept."""
        def broken(entry):
            raise RuntimeError("log table gone")
        session = _Session([{'id': 15, 'c': 'F0', 'e': 0, 'd': 'AA'}])
        client = transport.HardwareClient('192.0.2.1', on_log=broken, sleep=lambda s: None, session=session)
        with self.assertRaises(RuntimeError):
            client.cmd(15, 'F0')

    def test_the_fake_module_reports_a_skew_and_a_silence_once(self):
        backend = FakeBackend({'modules': {'10.0.0.1': {'devices': {1: {'F0': 'AA'}}}}},
                              faults={(1, 'F0'): 'skew'})
        log = []
        client = backend.client('10.0.0.1', on_log=log.append)
        self.assertEqual(client.cmd(1, 'F0').data, 'AA')
        self.assertTrue(log[0]['skewed'])
        self.assertEqual(log[1]['attempt'], 2)

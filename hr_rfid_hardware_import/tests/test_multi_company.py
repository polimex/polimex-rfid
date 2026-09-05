"""A survey and everything it read belong to one company."""
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import HwImportCase

#: Every model the survey persists, with the way it reaches its survey.
SURVEY_MODELS = {
    'hr.rfid.hw.import.module': 'run_id',
    'hr.rfid.hw.import.ctrl': 'run_id',
    'hr.rfid.hw.import.card': 'run_id',
    'hr.rfid.hw.import.card.record': 'card_id.run_id',
    'hr.rfid.hw.import.ts': 'run_id',
    'hr.rfid.hw.import.ts.slot': 'run_id',
    'hr.rfid.hw.import.group': 'run_id',
    'hr.rfid.hw.import.group.right': 'run_id',
    'hr.rfid.hw.import.person': 'run_id',
    'hr.rfid.hw.import.name': 'run_id',
    'hr.rfid.hw.import.issue': 'run_id',
    'hr.rfid.hw.import.cmd.log': 'run_id',
}


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_company')
class TestMultiCompany(HwImportCase):

    def test_another_company_cannot_see_the_survey_or_any_of_its_rows(self):
        run = self._survey(with_b=False)
        self._upload_names(run)
        other = self.env['res.company'].create({'name': 'Other survey company'})
        user = self.env['res.users'].create({
            'name': 'Other admin', 'login': 'other_survey_admin',
            'company_id': other.id, 'company_ids': [(6, 0, [other.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_system').id])],
        })
        Run = self.env['hr.rfid.hw.import.run'].with_user(user)
        self.assertFalse(Run.search([('id', '=', run.id)]))
        for model, path in SURVEY_MODELS.items():
            rows = self.env[model].sudo().search([(path, '=', run.id)])
            self.assertTrue(rows, "%s: the survey produced nothing to protect" % model)
            self.assertFalse(self.env[model].with_user(user).search([(path, '=', run.id)]), model)
            with self.assertRaises(AccessError, msg=model):
                rows.with_user(user).read(['id'])
        with self.assertRaises(AccessError):
            run.with_user(user).read(['name'])

    def test_the_own_company_sees_every_row(self):
        run = self._survey(with_b=False)
        self._upload_names(run)
        user = self.env['res.users'].create({
            'name': 'Own admin', 'login': 'own_survey_admin',
            'company_id': self.company.id, 'company_ids': [(6, 0, [self.company.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_system').id])],
        })
        for model, path in SURVEY_MODELS.items():
            expected = self.env[model].sudo().search_count([(path, '=', run.id)])
            self.assertEqual(self.env[model].with_user(user).search_count([(path, '=', run.id)]), expected, model)


def migrate(cr, version):
    cr.execute('''
ALTER TABLE hr_rfid_card_type
    DROP CONSTRAINT IF EXISTS hr_rfid_card_type_rfid_card_type_unique;
''')

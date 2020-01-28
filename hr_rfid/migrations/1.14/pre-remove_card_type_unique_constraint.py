
def migrate(cr, version):
    cr.execute('''
ALTER TABLE hr_rfid_card_type
    DROP CONSTRAINT hr_rfid_card_type_rfid_card_type_unique;
''')

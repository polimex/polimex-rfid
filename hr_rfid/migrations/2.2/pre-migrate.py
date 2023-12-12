from odoo.tools import drop_view_if_exists

def migrate(cr, version):
    # drop_view_if_exists(cr, 'hr_rfid_access_group_contact_rel_check_duplicates')
    cr.execute('ALTER TABLE hr_rfid_access_group_contact_rel DROP CONSTRAINT IF EXISTS hr_rfid_access_group_contact_rel_check_duplicates')
    # drop_view_if_exists(cr, 'hr_rfid_access_group_employee_rel_check_duplicates')
    cr.execute('ALTER TABLE hr_rfid_access_group_employee_rel DROP CONSTRAINT IF EXISTS hr_rfid_access_group_employee_rel_check_duplicates')

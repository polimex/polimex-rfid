from odoo.tools import drop_view_if_exists

def migrate(cr, version):
    # drop_view_if_exists(cr, 'hr_rfid_access_group_contact_rel_check_duplicates')
    # IF EXISTS on the TABLE too: pre-migrate runs before the ORM creates
    # tables, so on old databases these rel tables may not exist yet.
    cr.execute('ALTER TABLE IF EXISTS hr_rfid_access_group_contact_rel DROP CONSTRAINT IF EXISTS hr_rfid_access_group_contact_rel_check_duplicates')
    # drop_view_if_exists(cr, 'hr_rfid_access_group_employee_rel_check_duplicates')
    cr.execute('ALTER TABLE IF EXISTS hr_rfid_access_group_employee_rel DROP CONSTRAINT IF EXISTS hr_rfid_access_group_employee_rel_check_duplicates')

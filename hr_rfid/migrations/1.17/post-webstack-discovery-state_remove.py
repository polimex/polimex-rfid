def migrate(cr, version):
    # Rename table name
    cr.execute("alter table hr_rfid_webstack_discovery drop column state;")
    # Select debt journals
    # cr.execute('SELECT id FROM account_journal WHERE account_journal.debt is true')
    # Take the first journal
    # journal_id = cr.fetchone()
    # if journal_id:
        # set token one to all credit products
        # cr.execute('UPDATE product_template SET temporary_credit_product=%s WHERE credit_product is true', journal_id)

    # TODO:
    # Table 'hr_rfid_access_group_door_rel': unable to set NOT NULL on column 'alarm_rights'
    # Table 'hr_rfid_card_door_rel': unable to set NOT NULL on column 'alarm_right'
    # Deleting field hr.rfid.webstack.manual.create.webstack_address (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.webstack.discovery.state (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.webstack.discovery.setup_and_set_to_active (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.__last_update (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.write_date (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.write_uid (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.create_date (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.create_uid (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.display_name (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.id (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.text (hint: fields should be explicitly removed by an upgrade script)
    # The model hr.rfid.wiz.dialog.box could not be dropped because it did not exist in the registry.

    # Table 'hr_rfid_card_door_rel': unable to set NOT NULL on column 'alarm_right'
    # Table 'hr_rfid_access_group_door_rel': unable to set NOT NULL on column 'alarm_rights'

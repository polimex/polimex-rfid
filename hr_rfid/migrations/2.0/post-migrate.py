def migrate(cr, version):

    # Deleting field hr.rfid.webstack.discovery.state (hint: fields should be explicitly removed by an upgrade script)
    cr.execute("alter table hr_rfid_webstack_discovery drop column if exists state;")

    # Deleting field hr.rfid.webstack.manual.create.webstack_address (hint: fields should be explicitly removed by an upgrade script)
    cr.execute("alter table hr_rfid_webstack_manual_create drop column if exists webstack_address;")

    # Deleting field hr.rfid.webstack.discovery.setup_and_set_to_active (hint: fields should be explicitly removed by an upgrade script)
    cr.execute("alter table hr_rfid_webstack_discovery drop column if exists setup_and_set_to_active;")

    # Deleting field hr.rfid.wiz.dialog.box.__last_update (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.write_date (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.write_uid (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.create_date (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.create_uid (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.display_name (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.id (hint: fields should be explicitly removed by an upgrade script)
    # Deleting field hr.rfid.wiz.dialog.box.text (hint: fields should be explicitly removed by an upgrade script)
    # The model hr.rfid.wiz.dialog.box could not be dropped because it did not exist in the registry.
    cr.execute("drop table if exists hr_rfid_wiz_dialog_box;")

    # Table 'hr_rfid_access_group_door_rel': unable to set NOT NULL on column 'alarm_rights'
    cr.execute(" UPDATE hr_rfid_access_group_door_rel SET alarm_rights = false WHERE alarm_rights IS NULL;")
    cr.execute("ALTER TABLE hr_rfid_access_group_door_rel ALTER COLUMN alarm_rights SET NOT NULL;")


    # Table 'hr_rfid_card_door_rel': unable to set NOT NULL on column 'alarm_right'
    cr.execute(" UPDATE hr_rfid_card_door_rel SET alarm_right = false WHERE alarm_right IS NULL;")
    cr.execute("ALTER TABLE hr_rfid_card_door_rel ALTER COLUMN alarm_right SET NOT NULL;")

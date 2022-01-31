def migrate(cr, version):

    # Deleting field hr.rfid.webstack.discovery.state
    cr.execute("alter table hr_rfid_webstack_discovery drop column if exists state;")

    # Deleting field hr.rfid.webstack.manual.create.webstack_address
    cr.execute("alter table hr_rfid_webstack_manual_create drop column if exists webstack_address;")

    # Deleting field hr.rfid.webstack.discovery.setup_and_set_to_active
    cr.execute("alter table hr_rfid_webstack_discovery drop column if exists setup_and_set_to_active;")

    # Deleting field hr.rfid.wiz.dialog.box.__last_update
    # Deleting field hr.rfid.wiz.dialog.box.write_date
    # Deleting field hr.rfid.wiz.dialog.box.write_uid
    # Deleting field hr.rfid.wiz.dialog.box.create_date
    # Deleting field hr.rfid.wiz.dialog.box.create_uid
    # Deleting field hr.rfid.wiz.dialog.box.display_name
    # Deleting field hr.rfid.wiz.dialog.box.id
    # Deleting field hr.rfid.wiz.dialog.box.text
    # The model hr.rfid.wiz.dialog.box could not be dropped because it did not exist in the registry.
    cr.execute("drop table if exists hr_rfid_wiz_dialog_box;")

    # Table 'hr_rfid_access_group_door_rel': unable to set NOT NULL on column 'alarm_rights'
    cr.execute(" UPDATE hr_rfid_access_group_door_rel SET alarm_rights = false WHERE alarm_rights IS NULL;")
    cr.execute("ALTER TABLE hr_rfid_access_group_door_rel ALTER COLUMN alarm_rights SET NOT NULL;")


    # Table 'hr_rfid_card_door_rel': unable to set NOT NULL on column 'alarm_right'
    cr.execute(" UPDATE hr_rfid_card_door_rel SET alarm_right = false WHERE alarm_right IS NULL;")
    cr.execute("ALTER TABLE hr_rfid_card_door_rel ALTER COLUMN alarm_right SET NOT NULL;")

    # Deleting field hr.rfid.ctrl.command_ids
    cr.execute("alter table hr_rfid_ctrl drop column if exists command_ids;")
    # Deleting field hr.rfid.ctrl.system_event_ids
    cr.execute("alter table hr_rfid_ctrl drop column if exists system_event_ids;")
    # Deleting field hr.rfid.webstack.command_ids
    cr.execute("alter table hr_rfid_webstack drop column if exists command_ids;")
    # Deleting field hr.rfid.webstack.system_event_ids
    cr.execute("alter table hr_rfid_webstack drop column if exists system_event_ids;")
    # Deleting field hr.rfid.ctrl.alarm.system_event_ids
    cr.execute("alter table hr_rfid_ctrl_alarm drop column if exists system_event_ids;")
    # Deleting field hr.rfid.ctrl.alarm.user_event_ids
    cr.execute("alter table hr_rfid_ctrl_alarm drop column if exists user_event_ids;")
    # Deleting field hr.rfid.door.user_event_ids
    cr.execute("alter table hr_rfid_door drop column if exists user_event_ids;")
    # Deleting field hr.rfid.ctrl.alarm.system_event_ids
    cr.execute("alter table hr_rfid_ctrl_alarm drop column if exists system_event_ids;")
    # Deleting field hr.rfid.ctrl.alarm.user_event_ids
    cr.execute("alter table hr_rfid_ctrl_alarm drop column if exists user_event_ids;")
    # Deleting field hr.rfid.ctrl.command_ids
    cr.execute("alter table hr_rfid_ctrl drop column if exists commands_ids;")
    # Deleting field hr.rfid.ctrl.system_event_ids
    cr.execute("alter table hr_rfid_ctrl drop column if exists system_event_ids;")
    # Deleting field hr.rfid.card.user_event_ids
    cr.execute("alter table hr_rfid_card drop column if exists user_event_ids;")
    # Deleting field hr.rfid.webstack.command_ids
    cr.execute("alter table hr_rfid_webstack drop column if exists commands_ids;")
    # Deleting field hr.rfid.webstack.system_event_ids
    cr.execute("alter table hr_rfid_webstack drop column if exists system_event_ids;")

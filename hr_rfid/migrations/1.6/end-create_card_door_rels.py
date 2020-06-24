
def migrate(cr, version):
    cr.execute('''
    CREATE OR REPLACE FUNCTION create_card_door_rels() 
    RETURNS VOID AS $$
    DECLARE
        rec RECORD;
    BEGIN
        FOR rec IN SELECT 
                      DISTINCT card.id AS card_id, door_rel.door_id AS door_id,
                      door_rel.time_schedule_id AS ts_id
                   FROM hr_rfid_card AS card
                   LEFT JOIN hr_rfid_access_group_employee_rel AS emp_rel ON (emp_rel.employee_id = card.employee_id)
                   LEFT JOIN hr_rfid_access_group_contact_rel AS cont_rel ON (cont_rel.contact_id = card.contact_id)
                   JOIN hr_rfid_access_group_door_rel AS door_rel
                       ON (door_rel.access_group_id = emp_rel.access_group_id OR door_rel.access_group_id = cont_rel.access_group_id)
                   JOIN hr_rfid_door AS door ON (door.id = door_rel.door_id)
                   JOIN hr_rfid_ctrl AS ctrl ON (ctrl.id = door.controller_id)
                   WHERE card.card_type = door.card_type
                         AND card.active IS true
                         AND (card.cloud_card IS false OR ctrl.external_db IS false)
        LOOP
            INSERT INTO hr_rfid_card_door_rel(card_id, door_id, time_schedule_id)
            VALUES (rec.card_id, rec.door_id, rec.ts_id);
        END LOOP;
    END; 
    $$ LANGUAGE plpgsql;
    ''')

    cr.execute('SELECT create_card_door_rels();')
    cr.execute('DROP FUNCTION create_card_door_rels();')


def migrate(cr, version):
    ##############################################################################
    # Create function to migrate current data into the new reader_door_rel table #
    ##############################################################################
    cr.execute('''
CREATE OR REPLACE FUNCTION create_reader_door_rels()
RETURNS VOID AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT
                reader.id AS reader_id,
                door.id AS door_id
            FROM hr_rfid_reader AS reader
            LEFT JOIN hr_rfid_door AS door ON (door.id = reader.door_id)
            WHERE reader.id IS NOT NULL and door.id IS NOT NULL
    LOOP
        INSERT INTO hr_rfid_reader_door_rel(reader_id, door_id)
        VALUES (rec.reader_id, rec.door_id);
    END LOOP;
END;
$$ LANGUAGE plpgsql;
    ''')

    ################################
    # Call and delete the function #
    ################################
    cr.execute('SELECT create_reader_door_rels();')
    cr.execute('DROP FUNCTION create_reader_door_rels();')

    #######################################
    # Delete old column in hr_rfid_reader #
    #######################################
    cr.execute('''
ALTER TABLE hr_rfid_reader
DROP COLUMN door_id;
    ''')

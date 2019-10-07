
def migrate(cr, version):
    cr.execute('''
SELECT hr_rfid_vending_event.id, hr_rfid_vending_balance_history.id
    FROM hr_rfid_vending_event
    LEFT JOIN hr_rfid_vending_balance_history
        ON (CAST(hr_rfid_vending_event.create_date AS timestamp(0)) = CAST(hr_rfid_vending_balance_history.create_date AS timestamp(0)))
    WHERE
        item_sold IS NOT NULL
        AND hr_rfid_vending_event.employee_id IS NOT NULL
        AND event_action = '47'
    ORDER BY hr_rfid_vending_event.id desc;
    ''')
    for row in cr.fetchall():
        cr.execute('''
        UPDATE hr_rfid_vending_balance_history
            SET vending_event_id = %d
            WHERE id = %d
        '''
         % (row[0], row[1])
        )

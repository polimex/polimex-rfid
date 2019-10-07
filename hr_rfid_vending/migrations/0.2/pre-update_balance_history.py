
def migrate(cr, version):
    cr.execute('ALTER TABLE hr_rfid_vending_balance_history ADD COLUMN vending_event_id integer;')
    cr.execute('''
    ALTER TABLE public.hr_rfid_vending_balance_history
        ADD CONSTRAINT hr_rfid_vending_balance_history_vending_event_id_fkey FOREIGN KEY (vending_event_id)
        REFERENCES public.hr_rfid_vending_event (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE SET NULL;
    ''')

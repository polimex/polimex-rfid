# Polimex Holding Ltd. - https://polimex.co
"""Demo events were declared noupdate="False" and became deletion candidates
for ir.model.data._process_end on every database that stopped reloading demo
data. See hr_rfid/migration_utils.py for the full mechanism."""
from odoo.addons.hr_rfid.migration_utils import demo_records_to_noupdate


def migrate(cr, version):
    demo_records_to_noupdate(cr, "hr_rfid")

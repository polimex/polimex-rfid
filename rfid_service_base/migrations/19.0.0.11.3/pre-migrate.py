# Polimex Holding Ltd. - https://polimex.co
"""The demo services were declared noupdate="False", so an upgrade on a
database that no longer reloads demo tried to DELETE them - and the sold
services reference them through a RESTRICT foreign key, which aborted the whole
registry load. See hr_rfid/migration_utils.py for the full mechanism."""
from odoo.addons.hr_rfid.migration_utils import demo_records_to_noupdate


def migrate(cr, version):
    demo_records_to_noupdate(cr, "rfid_service_base")

# Polimex Holding Ltd. - https://polimex.co
"""P2 (endpoint delegation): back-fill polimex.ws.endpoint for existing modules
BEFORE the schema sync enforces the required endpoint_id. See
polimex_ws/migration_utils.py for the shared logic."""
from odoo.addons.polimex_ws.migration_utils import link_host


def migrate(cr, version):
    link_host(cr, "hr_rfid_webstack")

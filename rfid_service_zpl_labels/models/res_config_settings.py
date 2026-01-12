from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'
    
    # Label printer settings - related to company fields
    rfid_label_printer_ip = fields.Char(
        string='Label Printer IP',
        related='company_id.rfid_label_printer_ip',
        readonly=False,
        help='IP address of the Zebra label printer for wristband printing'
    )
    
    rfid_label_printer_port = fields.Integer(
        string='Label Printer Port', 
        related='company_id.rfid_label_printer_port',
        readonly=False,
        help='TCP port for the Zebra label printer connection (default: 9100)'
    )
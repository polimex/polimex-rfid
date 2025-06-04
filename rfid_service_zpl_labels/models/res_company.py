# models/company_logo_grf.py  – Polimex Dev Team
import base64
import io
import textwrap
from PIL import Image
from odoo import models, api, fields

class Company(models.Model):
    _inherit = "res.company"
    
    # Company-specific label printer settings
    rfid_label_printer_ip = fields.Char(
        string='Label Printer IP',
        help='IP address of the Zebra label printer for this company'
    )
    
    rfid_label_printer_port = fields.Integer(
        string='Label Printer Port',
        default=9100,
        help='TCP port for the Zebra label printer connection'
    )

    @api.model
    def _logo_as_grf(self, grf_name="COMPLOGO.GRF"):
        """Return (^XA~DG…^XZ) string ready to prepend to a ZPL job."""
        if not self.logo:
            return ""

        # 1) Decode and convert to 1-bit monochrome (required by ZPL)
        img = Image.open(io.BytesIO(base64.b64decode(self.logo)))
        img = img.convert("1")          # Floyd–Steinberg dithering

        width, height = img.size
        row_bytes = (width + 7) // 8
        total_bytes = row_bytes * height
        binary = bytearray()

        # 2) Pack pixels: 1 = black, 0 = white
        for y in range(height):
            byte = 0
            bit = 0
            for x in range(width):
                if img.getpixel((x, y)) == 0:
                    byte |= 1 << (7 - bit)
                bit += 1
                if bit == 8:
                    binary.append(byte)
                    byte = bit = 0
            if bit:                      # flush last partial byte
                binary.append(byte)

        hex_data = "".join(f"{b:02X}" for b in binary)
        # 3) Build the ~DG command (64-char wraps for readability)
        wrapped = "\n".join(textwrap.wrap(hex_data, 64))
        return f"^XA~DG{grf_name},{total_bytes},{row_bytes},{wrapped}^XZ"

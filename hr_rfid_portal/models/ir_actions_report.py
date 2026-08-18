# -*- coding: utf-8 -*-

from pathlib import Path
from odoo import api, models
from reportlab.graphics.shapes import Drawing as ReportLabDrawing, Image as ReportLabImage

# Ratio between the logo size and the QR-code size (about 15%)
POLIMEX_QR_LOGO_SIZE_RATIO = 0.1522
# Path to the Polimex logo for QR codes
POLIMEX_QR_LOGO_FILE = Path('../static/img/polimex_qr_logo.png')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_available_barcode_masks(self):
        rslt = super().get_available_barcode_masks()
        rslt['polimex_logo'] = self.apply_qr_code_polimex_logo_mask
        return rslt

    @api.model
    def apply_qr_code_polimex_logo_mask(self, width, height, barcode_drawing):
        assert isinstance(barcode_drawing, ReportLabDrawing)

        zoom_x = barcode_drawing.transform[0]
        zoom_y = barcode_drawing.transform[3]

        logo_width = POLIMEX_QR_LOGO_SIZE_RATIO * width
        logo_height = POLIMEX_QR_LOGO_SIZE_RATIO * height

        logo_path = Path(__file__).absolute().parent / POLIMEX_QR_LOGO_FILE

        qr_logo = ReportLabImage(
            (width / 2 - logo_width / 2) / zoom_x,
            (height / 2 - logo_height / 2) / zoom_y,
            logo_width / zoom_x,
            logo_height / zoom_y,
            logo_path.as_posix()
        )

        barcode_drawing.add(qr_logo)

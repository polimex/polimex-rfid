# -*- coding: utf-8 -*-
from odoo import fields, models


class CctvCameraDiagnostic(models.TransientModel):
    """The result screen of the camera self-test.

    A dialog rather than a notification: the report is long (every problem
    plus every detail of the device), and the operator reads it, copies it,
    or sends it to support. The same text is also posted in the camera's
    chatter, so past test runs remain comparable.
    """
    _name = 'cctv.camera.diagnostic'
    _description = 'Camera Self-Test Report'

    camera_id = fields.Many2one(
        'cctv.camera', required=True, readonly=True, ondelete='cascade',
        help="The camera this self-test was run against.",
    )
    report = fields.Text(
        readonly=True,
        help="Every problem found first, then every detail the camera "
             "reported. The same text is kept in the camera's chatter.",
    )

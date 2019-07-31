from odoo import fields, models


class DialogBox(models.TransientModel):
    _name = 'hr.rfid.wiz.dialog.box'

    title = fields.Char()
    text = fields.Char()


def create_dialog_box(env, title: str, text: str):
    return env['hr.rfid.wiz.dialog.box'].create([{
        'title': title,
        'text': text,
    }])


def return_dialog_box(d_box: DialogBox):
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'hr.rfid.wiz.dialog.box',
        'view_mode': 'form',
        'view_type': 'form',
        'res_id': d_box.id,
        'views': [(False, 'form')],
        'target': 'new',
    }


def create_and_ret_d_box(env, title: str, text: str):
    d_box = create_dialog_box(env, title, text)
    return return_dialog_box(d_box)





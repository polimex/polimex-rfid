from odoo import fields, models


class DialogBox(models.TransientModel):
    _name = 'hr.rfid.wiz.dialog.box'

    title = fields.Char(string='Title', readonly=True)
    text = fields.Char(string='Text', readonly=True)


def return_wiz_form_view(res_model: str, res_id: int):
    return {
        'type': 'ir.actions.act_window',
        'res_model': res_model,
        'view_mode': 'form',
        'view_type': 'form',
        'res_id': res_id,
        'views': [(False, 'form')],
        'target': 'new',
    }


def create_dialog_box(env, title: str, text: str):
    return env['hr.rfid.wiz.dialog.box'].create([{
        'title': title,
        'text': text,
    }])


def return_dialog_box(d_box: DialogBox):
    return return_wiz_form_view('hr.rfid.wiz.dialog.box', d_box.id)


def create_and_ret_d_box(env, title: str, text: str):
    d_box = create_dialog_box(env, title, text)
    return return_dialog_box(d_box)





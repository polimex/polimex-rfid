
from odoo.api import Environment
from odoo import models
from ..models.hr_rfid_webstack import HrRfidWebstack, HrRfidController
from random import randint


def create_webstacks(env: Environment, webstacks: int = 0, controllers: list = None):
    """
    Creates a set number of webstacks
    :param env: Environment
    :param webstacks: Number of webstacks to create
    :param controllers: A list of modes the controllers should be for the webstacks. Example:
                        [1, 2]: would create 2 controllers per webstack, the first one with mode 1
                                and the second one with mode 2
    :return: Recordset with all the webstacks
    """
    if controllers is None:
        controllers = []

    def _create_wss():
        _records = env['hr.rfid.webstack']
        _ws_env = env['hr.rfid.webstack']

        def gen_serial(cur_webstacks):
            _cur_serials = cur_webstacks.mapped('serial')

            while True:
                _serial = str(randint(400000, 499999))
                if _serial not in _cur_serials:
                    return _serial

        for i in range(webstacks):
            serial = gen_serial(_records)

            _records += _ws_env.create({
                'name': 'Module ' + serial,
                'serial': serial,
                'key': '0000',
                'ws_active': True,
                'version': '9.99',
                'behind_nat': False,
                'last_ip': '0.0.0.0',
            })
        return _records

    def _create_ctrl(_ws: HrRfidWebstack, _mode: int):
        _ctrl_env = env['hr.rfid.ctrl']
        _door_env = env['hr.rfid.door']
        _reader_env = env['hr.rfid.reader']

        def _gen_id():
            _cur_ids = _ws.controllers.mapped('ctrl_id')
            while True:
                _new_id = randint(1, 254)
                if _new_id == 0xCB or _new_id == 0xCE:
                    continue
                if _new_id not in _cur_ids:
                    return _new_id

        def _gen_door_name(_door_num, _ctrl_id):
            return 'Door ' + str(_door_num) + ' of ctrl ' + str(_ctrl_id)

        def _create_door(_name, _number, _ctrl_id):
            return _door_env.create({
                'name': _name,
                'number': _number,
                'controller_id': _ctrl_id,
            })

        def _create_reader(_name, _number, _reader_type, _ctrl_id, _door_id):
            _reader_env.create({
                'name': _name,
                'number': _number,
                'reader_type': _reader_type,
                'controller_id': _ctrl_id,
                'door_id': _door_id,
            })

        _external_db = _mode & 0x20 > 0
        _mode = _mode & 0x0F
        _id = _gen_id()

        _ctrl = _ctrl_env.create({
            'name': 'Controller ' + str(_id),
            'ctrl_id': _id,
            'hw_version': '17',
            'serial_number': '0',
            'sw_version': '999',
            'external_db': _external_db,
            'mode': _mode,
            'webstack_id': _ws.id,
        })

        if _mode == 1 or _mode == 3:
            _door = _create_door(_gen_door_name(1, _ctrl.id), 1, _ctrl.id)
            _create_reader('R1', 1, '0', _ctrl.id, _door)
            _create_reader('R2', 2, '1', _ctrl.id, _door)
        else:  # (_mode == 2 and readers_count == 2) or _mode == 4
            _door = _create_door(_gen_door_name(1, _ctrl.id), 1, _ctrl.id)
            _create_reader('R1', 1, '0', _ctrl.id, _door)
            _door = _create_door(_gen_door_name(2, _ctrl.id), 2, _ctrl.id)
            _create_reader('R2', 2, '0', _ctrl.id, _door)

        if _mode == 3:
            _door = _create_door(_gen_door_name(2, _ctrl.id), 2, _ctrl.id)
            _create_reader('R3', 3, '0', _ctrl.id, _door)
            _door = _create_door(_gen_door_name(3, _ctrl.id), 3, _ctrl.id)
            _create_reader('R4', 4, '0', _ctrl.id, _door)
        elif _mode == 4:
            _door = _create_door(_gen_door_name(3, _ctrl.id), 3, _ctrl.id)
            _create_reader('R3', 3, '0', _ctrl.id, _door)
            _door = _create_door(_gen_door_name(4, _ctrl.id), 4, _ctrl.id)
            _create_reader('R4', 4, '0', _ctrl.id, _door)

    records = _create_wss()
    for ws in records:
        for mode in controllers:
            _create_ctrl(ws, mode)

    return records


def create_acc_grs_nms(env: Environment, names: list = None):
    """
    Create access groups
    :param env: Environment
    :param names: Names of access groups in a list
    :return: Set with the access groups
    """
    records = env['hr.rfid.access.group']
    acc_gr_env = records

    if names is None:
        return records

    for name in names:
        records += acc_gr_env.create({
            'name': name,
        })

    return records


def create_acc_grs_cnt(env: Environment, count: int = 0):
    """
    Create access groups
    :param env: Environment
    :param count: Number of access groups to create
    :return: Set with the access groups
    """
    records = env['hr.rfid.access.group']
    acc_gr_env = records

    for __ in range(0, count):
        records += acc_gr_env.create({})

    return records


def create_departments(env: Environment, names: list = None):
    records = env['hr.department']
    dep_env = records

    if names is None:
        return records

    for name in names:
        records += dep_env.create({
            'name': name,
        })

    return records


def create_employees(env: Environment, names: list = None, departments: list = None):
    records = env['hr.employee']
    emp_env = records

    if names is None:
        return records
    if departments is None:
        departments = []

    dep_it = 0

    for name in names:
        emp_dict = {
            'name': name,
        }
        if dep_it < len(departments):
            emp_dict['department_id'] = departments[dep_it].id
            dep_it += 1
        records += emp_env.create(emp_dict)

    return records


def create_contacts(env: Environment, names: list = None):
    records = env['res.partner']
    contact_env = records

    if names is None:
        return records

    for name in names:
        records += contact_env.create({
            'name': name,
        })

    return records


def create_card(env: Environment, number: str, owner: models.BaseModel, card_type=None, activate_on=None,
                deactivate_on=None, card_active=None, cloud_card=None):
    card_dict = {
        'number': number,
    }
    if 'hr.employee' in str(owner.__class__):
        card_dict['employee_id'] = owner.id
    else:
        card_dict['contact_id'] = owner.id

    if card_type is not None:
        card_dict['card_type'] = card_type

    if activate_on is not None:
        card_dict['activate_on'] = activate_on

    if deactivate_on is not None:
        card_dict['deactivate_on'] = deactivate_on

    if card_active is not None:
        card_dict['card_active'] = card_active

    if cloud_card is not None:
        card_dict['cloud_card'] = cloud_card

    return env['hr.rfid.card'].create(card_dict)



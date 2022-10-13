MAX_DIRECT_EXECUTE = 10  # command count for direct execute
MAX_DIRECT_EXECUTE_TIME = 5  # last X seconds for counting executed cmds

"""Polimex Hardware version list"""
HW_TYPES = [('1', 'iCON200'), ('2', 'iCON150'), ('3', 'iCON150'), ('4', 'iCON140'),
            ('5', 'iCON120'), ('6', 'iCON110'), ('7', 'iCON160'), ('8', 'iCON170'),
            ('9', 'Turnstile'), ('10', 'iCON180'), ('11', 'iCON115'), ('12', 'iCON50'),
            ('13', 'FireControl'), ('14', 'FireControl'), ('18', 'FireControl'),
            ('19', 'FireControl'), ('15', 'TempRH'), ('16', 'Vending'), ('17', 'iCON130'),
            ('20', 'AlarmControl'), ('21', 'AlarmControl'), ('22', 'AlarmControl'),
            ('23', 'AlarmControl'), ('26', 'AlarmControl'), ('27', 'AlarmControl'),
            ('28', 'AlarmControl'), ('29', 'AlarmControl'), ('24', 'iTemp'), ('25', 'iGas'),
            ('30', 'RelayControl110'), ('31', 'RelayControl'), ('32', 'RelayControl'),
            ('33', 'RelayControl'), ('34', 'RelayControl'), ('35', 'RelayControl'),
            ('36', 'RelayControl'), ('37', 'RelayControl'), ('38', 'RelayControl'),
            ('39', 'RelayControl'), ('40', 'MFReader'), ('41', 'MFReader'), ('42', 'MFReader'),
            ('43', 'MFReader'), ('44', 'MFReader'), ('45', 'MFReader'), ('46', 'MFReader'),
            ('47', 'MFReader'), ('48', 'MFReader'), ('49', 'MFReader'), ('50', 'iMotor')]
DEFAULT_IO_TABLES = [
    # [hw_version, mode, data]
    # iCON110
    [6, 2,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x4, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
    [6, 1,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
    # Turnstile
    [9, 1,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x5,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x5, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x5, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x5, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0xA, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x5, 0x5,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x5,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x5, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x5, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x5, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x80, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
    # iCON180
    [10, 2,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x3,
      0x0, 0x0, 0x5, 0x5, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x63, 0x0, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1E, 0x00,  # 20 AUTO ARM(8,7,6,5),SIREN ON/OFF (2,1)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0xA, 0xA, 0xA, 0xA,  # 27  DELAY ARM (OUT)
      0x0, 0x0, 0x0, 0x0, 0x14, 0x14, 0x14, 0x14]  # 28 DELAY DISARM (IN)

     ],
    [10, 3,
     [0x0, 0x0, 0x0, 0x0, 0x3, 0x3, 0x0, 0x3,
      0x0, 0x5, 0x5, 0x5, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x63, 0x63, 0x0, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1E, 0x00,  # 20 AUTO ARM(8,7,6,5),SIREN ON/OFF (2,1)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0xA, 0xA, 0xA, 0xA,  # 27  DELAY ARM (OUT)
      0x0, 0x0, 0x0, 0x0, 0x14, 0x14, 0x14, 0x14]  # 28 DELAY DISARM (IN)

     ],
    [10, 4,
     [0x0, 0x0, 0x0, 0x0, 0x3, 0x3, 0x3, 0x3,
      0x5, 0x5, 0x5, 0x5, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x63, 0x63, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1E, 0x00,  # 20 AUTO ARM(8,7,6,5),SIREN ON/OFF (2,1)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0xA, 0xA, 0xA, 0xA,  # 27  DELAY ARM (OUT)
      0x0, 0x0, 0x0, 0x0, 0x14, 0x14, 0x14, 0x14]  # 28 DELAY DISARM (IN)
     ],
    # iCON115
    [11, 1,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1E, 0x0,  # 20 AUTO ARM(6,5),SIREN ON/OFF (2,1)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x4, 0x4, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x0, 0x0, 0x0, 0x0, 0x4, 0x4, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0xA,  # 27  DELAY ARM (OUT)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x14]  # 28 DELAY DISARM (IN)
     ],
    [11, 2,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x5, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x63, 0x63, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1E, 0x0,  # 20 AUTO ARM(6,5),SIREN ON/OFF (2,1)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x4, 0x4, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x0, 0x0, 0x0, 0x0, 0x4, 0x4, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0xA,  # 27  DELAY ARM (OUT)
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x14]  # 28 DELAY DISARM (IN)

     ],
    # iCON50
    [12, 1,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
    # iCON130
    [17, 2,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x3,
      0x0, 0x0, 0x5, 0x5, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
    [17, 3,
     [0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x3, 0x3,
      0x0, 0x5, 0x5, 0x5, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x63, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
    [17, 4,
     [0x0, 0x0, 0x0, 0x0, 0x3, 0x3, 0x3, 0x3,
      0x5, 0x5, 0x5, 0x5, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x3, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x63, 0x63, 0x63, 0x63,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x3, 0x0, 0x0, 0x0,
      0x4, 0x4, 0x4, 0x4, 0x1, 0x1, 0x1, 0x1,  # 25 delay overtime, door overtime
      0x4, 0x4, 0x4, 0x4, 0x0, 0x0, 0x0, 0x0,  # 26 forcet open
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
      0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
     ],
]


def get_default_io_table(hw_version: int, mode: int, as_string=True):
    for line in DEFAULT_IO_TABLES:
        if line[0] == hw_version and line[1] == mode:
            if as_string:
                return ''.join(["%02x" % i for i in line[2]])
            else:
                return line[2]


def bytes_to_num(data: str, start: int, digits: int):
    digits = digits - 1
    res = 0
    for j in range(digits + 1):
        multiplier = 10 ** (digits - j)
        res = res + int(data[start:start + 2], 16) * multiplier
        start = start + 2
    return res

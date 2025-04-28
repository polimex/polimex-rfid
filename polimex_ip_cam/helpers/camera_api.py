import requests
import xml.etree.ElementTree as ET
from requests.auth import HTTPDigestAuth
import logging
import base64

_logger = logging.getLogger(__name__)

VEHICLE_LOGO_MAP = {
    1026: "ALFAROMEO",
    1027: "ASTONMARTIN",
    1028: "AUDI",
    1030: "PORSCHE",
    1031: "BUICK",
    1032: "BJQICHE",
    1033: "BQZHIDAO",
    1034: "BQWEIWANG",
    1035: "BQYINXIANG",
    1036: "BENZ",
    1037: "BMW",
    1038: "BAOJUN",
    1039: "BAOLONG",
    1040: "BENTLEY",
    1041: "BRABUS",
    1043: "HONDA",
    1044: "PEUGEOT",
    1045: "BYD",
    1046: "CHANGHE",
    1048: "GREATWALL",
    1049: "CHANGAN",
    1050: "DS",
    1051: "SOUEAST",
    1053: "VOLKSWAGEN",
    1054: "DADI",
    1056: "DODGE",
    1059: "DAIHATSU",
    1060: "TOYOTA",
    1063: "FEREARI",
    1064: "FORD",
    1066: "FUDI",
    1067: "FIAT",
    1069: "MITSUOKA",
    1070: "GZYUNBAO",
    1071: "GQCHUANQI",
    1074: "QOROS",
    1076: "HUAPU",
    1077: "HUATAI",
    1078: "HAFEI",
    1079: "HUMMER",
    1080: "HAIMA",
    1081: "HONGQI",
    1083: "GEELYAUTO",
    1084: "JEEP",
    1085: "JAGUAR",
    1086: "JIANGNAN",
    1088: "CHRYSLER",
    1089: "CADILLAC",
    1091: "KANDIONE",
    1093: "LAMBORGHINI",
    1094: "LIFAN",
    1095: "ROLLSROYCE",
    1096: "LINCOLN",
    1097: "EVERUS",
    1098: "LIANHUA",
    1100: "LOTUS",
    1101: "LANDROVER",
    1102: "SUZUKI",
    1103: "LUFENG",
    1104: "LEXUS",
    1105: "RENAULT",
    1107: "MINI",
    1108: "MASERATI",
    1109: "MEIYA",
    1110: "MCLAREN",
    1111: "MAYBACH",
    1112: "MAZDA",
    1114: "LUXGEN",
    1115: "NJJINLONG",
    1116: "OPEL",
    1117: "ACURA",
    1119: "VENUCIA",
    1120: "CHERY",
    1121: "KIA",
    1123: "NISSAN",
    1124: "RUIQI",
    1125: "ROEWE",
    1127: "SMART",
    1128: "MITSUBISHI",
    1129: "SQDATONG",
    1131: "SHUANGHUAN",
    1132: "SHUANGLONG",
    1133: "SUBARU",
    1134: "SKODA",
    1135: "SAAB",
    1138: "TIANMA",
    1139: "TEALA",
    1141: "DENZA",
    1143: "WEILIN",
    1144: "VOLVO",
    1145: "WCYINGZHI",
    1146: "XINKAI",
    1147: "XINDADI",
    1148: "XINYATU",
    1149: "HYUNDAI",
    1150: "SEAT",
    1151: "CHEVROLET",
    1152: "CITROEN",
    1154: "YONGYUAN",
    1156: "INFINITI",
    1157: "MUSTANG",
    1159: "YUJIE",
    1160: "ZXAUTO",
    1161: "ZHONGHUA",
    1163: "ZOTYE",
    1164: "KNOWBEANS",
    1165: "KAIYI",
    1166: "HUASONG",
    1167: "JXWUSHILING",
    1168: "BORGWARD",
    1169: "SQTONGJIA",
    1170: "HANJIANG",
    1171: "ZINORO",
    1172: "LUDIFANGZHOU",
    1173: "HANTENG",
    1175: "CHANGJIANG",
    1176: "SWM",
    1177: "KEYTON",
    1180: "BISU",
    1181: "CAKUAYUE",
    1537: "ANKAI",
    1538: "ANYUAN",
    1540: "BBZHONGQI",
    1546: "CHENGGONG",
    1547: "CHANGLONG",
    1549: "CASHANGYONG",
    1552: "DONGFENG",
    1554: "DAEWOO",
    1555: "DAYUN",
    1556: "DIMA",
    1557: "DONGWO",
    1559: "FUTIAN",
    1561: "GMC",
    1562: "GQJIAO",
    1566: "HUALING",
    1570: "HUIZHONG",
    1571: "HIGER",
    1574: "HTYUANTONG",
    1575: "HANGTIAN",
    1576: "HUANGHAI",
    1577: "HEIBAO",
    1578: "JIULONG",
    1579: "JIANGHUAI",
    1580: "JIANGHUAN",
    1581: "JIANGLING",
    1584: "JINBEI",
    1585: "JINLONG",
    1586: "KAIMA",
    1587: "KAWEI",
    1588: "KAIRUI",
    1590: "LIANHE",
    1592: "MAN",
    1594: "NONGYONGCHE",
    1596: "NANJUN",
    1597: "QINGLING",
    1598: "YOUNGMANONE",
    1599: "SYZHONGGONG",
    1600: "SHSHITONG",
    1602: "TRICYCLE",
    1603: "SQYWKHY",
    1606: "SHAOLIN",
    1608: "SHIFENG",
    1609: "SUNWIN",
    1611: "SHENYE",
    1612: "SHUCHI",
    1613: "SHANQI",
    1614: "SCANIA",
    1615: "TANGJUN",
    1619: "WANFENG",
    1620: "WUZHENG",
    1621: "WULING",
    1626: "XUGONG",
    1629: "FAW",
    1630: "YAXING",
    1631: "IVECO",
    1633: "YUTONG",
    1634: "YANGZI",
    1635: "YANTAI",
    1636: "YUEJIN",
    1637: "YINTIAN",
    1639: "ZGZHONGQI",
    1641: "ZHONGTONGONE",
    1642: "ZHONGSHUN",
    1644: "ZHONGDA",
    1646: "JGZHONGKA",
    1647: "WUZHOULONG",
    1648: "COACH",
    1651: "PICKUP",
    1654: "JIJIANG",
    1674: "DONGFANGHONG",
    1676: "QINGQI",
    1677: "TRUCK",
    1678: "SPYCAR",
    1679: "TRAILCAR",
    1683: "GUILIN",
    1684: "SCHYUNDAI",
    1688: "WANXIANG",
    1690: "LFSHIJUN",
    1691: "CHANGAN",
    1692: "ZLZHONGGONG",
    1693: "YINLONG",
    1695: "YIXING",
    1696: "XIWO",
    1697: "YANGZIJIANG",
    1698: "SUITONG",
    1702: "ZHONGTIANFC",
    1703: "WANDA",
    1704: "SHANGRAO",
    1705: "ZHONGZHI",
    1706: "ZCSDDIANDONG",
    1707: "ZHONGTONGTWO",
    1708: "GLCOACH",
    1709: "BEIJING",
    1710: "BEIFANG",
    1711: "BFNAPULAN",
    1712: "HUACHUAN",
    1713: "YOUYI",
    1714: "TONGXIN",
    1715: "MG",
    1716: "JIACHUAN",
    1717: "NVSHEN",
    1718: "SHILI",
    1719: "SHAOLINTWO"
}


class BaseCamera:
    """
    Base universal camera class.

    Defines the interface for common camera operations.
    Subclasses (например HikvisionCamera) трябва да имплементират всички абстрактни методи.

    Методи, които трябва да се реализират:
      - check_connection(): Проверка на връзката и извличане на основна информация за устройството.
      - set_http_host(): Конфигуриране на HTTP host настройките.
      - add_plate_to_list(): Добавяне на регистрационен номер към списък (например whitelist).
      - delete_plate_from_list(): Изтриване на регистрационен номер от списък.
      - barrier_gate_control(): Управление на бариерната врата.
      - get_snapshot(): Извличане на снимка от камерата.
    """

    def __init__(self, ip_address, port, username, password, timeout=5):
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    def __enter__(self):
        # Тук може да се извърши начална инициализация, ако е нужна
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Тук може да се извърши освобождаване на ресурси, ако е нужно
        pass

    def check_connection(self):
        raise NotImplementedError("Subclasses must implement check_connection()")

    def set_http_host(self, host_ip, port_no, url_path):
        raise NotImplementedError("Subclasses must implement set_http_host()")

    def add_plate_to_list(self, plate_number, list_type):
        raise NotImplementedError("Subclasses must implement add_plate_to_list()")

    def delete_plate_from_list(self, plate_number):
        raise NotImplementedError("Subclasses must implement delete_plate_from_list()")

    def barrier_gate_control(self, operation, gate_num):
        raise NotImplementedError("Subclasses must implement barrier_gate_control()")

    def get_snapshot(self):
        raise NotImplementedError("Subclasses must implement get_snapshot()")


class HikvisionCamera(BaseCamera):
    """
    Hikvision-specific implementation of the camera interface.

    Този клас имплементира операциите за комуникация с камерата чрез ISAPI ендпойнти.
    Поддържа операции като проверка на връзката, конфигурация на HTTP host, управление на
    бариери, добавяне/изтриване на регистрационни номера и синхронизация на времето.
    """

    def _extract_error(self, response_text):
        """
        Опитва се да извлече детайлите за грешката от XML отговора на камерата.
        Ако успее, връща низ с информация за statusCode, statusString и subStatusCode.
        В противен случай, връща оригиналния текст.
        """
        try:
            root = ET.fromstring(response_text)
            ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}
            status_code = root.findtext('ns:statusCode', default='Unknown', namespaces=ns)
            status_string = root.findtext('ns:statusString', default='', namespaces=ns)
            sub_status_code = root.findtext('ns:subStatusCode', default='', namespaces=ns)
            error_details = f"Status Code: {status_code}, Message: {status_string}"
            if sub_status_code:
                error_details += f", SubStatus: {sub_status_code}"
            return error_details
        except Exception as e:
            return response_text

    def check_connection(self):
        """
        Проверява връзката към камерата и извлича основна информация за устройството.

        Използва GET заявка към: /ISAPI/System/deviceInfo

        Връща речник с ключове като:
          - status: "connected" или "failed"
          - name: Името на устройството
          - type: Типът на устройството
          - devid: Идентификатор на устройството
          - model: Модел на камерата
          - serial: Серийния номер
          - subserial: Подсерийния номер (ако има)
          - firmware: Версия на фърмуера
          - firmwaredate: Дата на пускане на фърмуера
          - hardware: Версия на хардуера
          - supportBeep: Поддържани функции (например звуков сигнал)
          - supportVideoLoss: Индикация за видео загуба

        Ако има грешка по време на заявката или XML парсинга, се връща статус "failed" с описание на грешката.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/System/deviceInfo"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            if response.status_code == 200:
                ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}
                try:
                    root = ET.fromstring(response.text)
                    name = root.findtext('.//ns:deviceName', namespaces=ns)
                    dev_type = root.findtext('.//ns:deviceType', namespaces=ns)
                    devid = root.findtext('.//ns:deviceID', namespaces=ns)
                    model = root.findtext('.//ns:model', namespaces=ns)
                    serial = root.findtext('.//ns:serialNumber', namespaces=ns)
                    subserial = root.findtext('.//ns:subSerialNumber', namespaces=ns)
                    firmware = root.findtext('.//ns:firmwareVersion', namespaces=ns)
                    firmwaredate = root.findtext('.//ns:firmwareReleasedDate', namespaces=ns)
                    hardware = root.findtext('.//ns:hardwareVersion', namespaces=ns)
                    supportBeep = root.findtext('.//ns:supportBeep', namespaces=ns)
                    supportVideoLoss = root.findtext('.//ns:supportVideoLoss', namespaces=ns)
                    _logger.debug("Hikvision check_connection: SUCCESS. Model: %s, Serial: %s, Firmware: %s",
                                  model, serial, firmware)
                    return {"status": "connected",
                            "name": name,
                            "type": dev_type,
                            "devid": devid,
                            "model": model,
                            "serial": serial,
                            "subserial": subserial,
                            "firmware": firmware,
                            "firmwaredate": firmwaredate,
                            "hardware": hardware,
                            "supportBeep": supportBeep,
                            "supportVideoLoss": supportVideoLoss}
                except Exception as e:
                    _logger.error("Hikvision check_connection: XML parsing error: %s", e)
                    return {"status": "failed", "error": str(e)}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision check_connection: Failed with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision check_connection: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def get_http_host(self):
        """
        Извлича текущата HTTP host конфигурация от камерата.

        Използва GET заявка към: /ISAPI/Event/notification/httpHosts/1

        Връща речник със следните ключове:
          - id, url, protocolType, parameterFormatType, addressingFormatType, ipAddress, portNo, userName,
            httpAuthenticationMethod, enabled
          - ANPR: Поддържа ключ detectionUpLoadPicturesType. Възможни стойности:
              "all"           - Изпраща както картинка на регистрационния номер, така и изображение на целия кадър.
              "licensePlate"  - Изпраща само картинката на регистрационния номер.
              "detection"     - Изпраща само изображението на детекцията.
              "none"          - Не изпраща никакви картинки.
          - SubscribeEvent: Поддържа ключове heartbeat и eventMode. Възможни стойности за eventMode:
              "all"    - Абониране за всички събития.
              "alarm"  - Абониране само за алармени събития.
              "none"   - Не се абонира за събития.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/Event/notification/httpHosts/1"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=5)
            if response.status_code == 200:
                xml_response = response.text.strip()
                root = ET.fromstring(xml_response)
                ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}
                result = {
                    'id': root.findtext('ns:id', namespaces=ns),
                    'url': root.findtext('ns:url', namespaces=ns),
                    'protocolType': root.findtext('ns:protocolType', namespaces=ns),
                    'parameterFormatType': root.findtext('ns:parameterFormatType', namespaces=ns),
                    'addressingFormatType': root.findtext('ns:addressingFormatType', namespaces=ns),
                    'ipAddress': root.findtext('ns:ipAddress', namespaces=ns),
                    'portNo': root.findtext('ns:portNo', namespaces=ns),
                    'userName': root.findtext('ns:userName', namespaces=ns),
                    'httpAuthenticationMethod': root.findtext('ns:httpAuthenticationMethod', namespaces=ns),
                    'ANPR': {
                        'detectionUpLoadPicturesType': root.findtext('ns:ANPR/ns:detectionUpLoadPicturesType',
                                                                     namespaces=ns)
                    },
                    'SubscribeEvent': {
                        'heartbeat': root.findtext('ns:SubscribeEvent/ns:heartbeat', namespaces=ns),
                        'eventMode': root.findtext('ns:SubscribeEvent/ns:eventMode', namespaces=ns)
                    },
                    'enabled': root.findtext('ns:enabled', namespaces=ns)
                }
                _logger.debug("Hikvision get_http_host: Parsed response: %s", result)
                return {"status": "success", "response": result}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision get_http_host: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision get_http_host: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def set_http_host(self, config):
        """
        Конфигурира HTTP host настройките на камерата.

        Параметър config трябва да е речник, съдържащ:
          - id: Идентификатор (дефолт: '1')
          - url: URL път (дефолт: '/ipcam/anpr/event')
          - protocolType: Протокол (дефолт: 'HTTP')
          - parameterFormatType: Формат на параметрите (дефолт: 'XML')
          - addressingFormatType: Формат на адреса (дефолт: 'ipaddress')
          - ipAddress: IP адрес за обратна връзка
          - portNo: Порт (дефолт: '')
          - userName: Потребителско име (дефолт: '')
          - httpAuthenticationMethod: Метод за HTTP автентикация (дефолт: 'none'), 'Digest', 'Basic'
          - ANPR: Речник със следния ключ:
              detectionUpLoadPicturesType - възможни стойности:
                  "all", "licensePlate", "detection", "none"
          - SubscribeEvent: Речник със следните ключове:
              heartbeat - интервал на пулса
              eventMode - възможни стойности: "all", "alarm", "none"
          - enabled: Флаг за активиране (дефолт: 'false')

        XML документът се създава с помощта на ElementTree и се изпраща чрез PUT заявка към:
          /ISAPI/Event/notification/httpHosts/1
        """
        # Извличане на параметрите с дефолтни стойности
        id_val = config.get('id', '1')
        url_path = config.get('url', '/ipcam/anpr/event')
        protocolType = config.get('protocolType', 'HTTP')
        parameterFormatType = config.get('parameterFormatType', 'XML')
        addressingFormatType = config.get('addressingFormatType', 'ipaddress')
        ipAddress = config.get('ipAddress', '')
        portNo = config.get('portNo', '')
        userName = config.get('userName', '')
        httpAuthenticationMethod = config.get('httpAuthenticationMethod', 'none')
        anpr = config.get('ANPR', {})
        detectionUpLoadPicturesType = anpr.get('detectionUpLoadPicturesType', 'all')
        subscribe = config.get('SubscribeEvent', {})
        heartbeat = subscribe.get('heartbeat', '')
        eventMode = subscribe.get('eventMode', 'all')
        enabled = config.get('enabled', 'false')

        # Създаване на XML чрез ElementTree
        root = ET.Element("HttpHostNotification", version="2.0", xmlns="http://www.isapi.org/ver20/XMLSchema")
        ET.SubElement(root, "id").text = id_val
        ET.SubElement(root, "url").text = url_path
        ET.SubElement(root, "protocolType").text = protocolType
        ET.SubElement(root, "parameterFormatType").text = parameterFormatType
        ET.SubElement(root, "addressingFormatType").text = addressingFormatType
        ET.SubElement(root, "ipAddress").text = ipAddress
        ET.SubElement(root, "portNo").text = portNo
        ET.SubElement(root, "userName").text = userName
        ET.SubElement(root, "httpAuthenticationMethod").text = httpAuthenticationMethod

        # ANPR блок – определя кой тип на изображение да се качва
        anpr_elem = ET.SubElement(root, "ANPR")
        ET.SubElement(anpr_elem, "detectionUpLoadPicturesType").text = detectionUpLoadPicturesType

        # SubscribeEvent блок – настройка на абонамента за събития
        subscribe_elem = ET.SubElement(root, "SubscribeEvent")
        ET.SubElement(subscribe_elem, "heartbeat").text = heartbeat
        ET.SubElement(subscribe_elem, "eventMode").text = eventMode

        ET.SubElement(root, "enabled").text = enabled

        xml_body = ET.tostring(root, encoding="utf-8", method="xml")

        try:
            response = requests.put(
                f"http://{self.ip_address}:{self.port}/ISAPI/Event/notification/httpHosts/1",
                auth=HTTPDigestAuth(self.username, self.password),
                data=xml_body,
                timeout=5
            )
            if response.status_code == 200:
                _logger.debug("Hikvision set_http_host: SUCCESS. Response: %s", response.text.strip())
                return {"status": "success", "response": response.text.strip()}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision set_http_host: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision set_http_host: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def add_plate_to_list(self, plate_entries):
        """
        Add one or more plates to the camera’s whitelist/blacklist via ISAPI.

        plate_entries: list of dicts, each with keys:
          - plateNum (str): license plate
          - listType (int|str): 0=whitelist,1=blacklist,… default 0
          - startTime (ISO8601 str): e.g. "2025-04-23T08:03:34Z"
          - endTime   (ISO8601 str): e.g. "0000-00-00T00:00:00Z"
          - cardNo    (str, optional): secondary ID
        """
        import xml.etree.ElementTree as ET
        from requests.auth import HTTPDigestAuth
        import requests

        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/VCL"

        # 1) Build XML
        ns = "http://www.isapi.org/ver20/XMLSchema"
        root = ET.Element("SetVCLData", {"version": "2.0", "xmlns": ns})
        vcl_list = ET.SubElement(root, "VCLDataList")

        for entry in plate_entries:
            single = ET.SubElement(vcl_list, "singleVCLData")
            ET.SubElement(single, "id").text = "0"
            ET.SubElement(single, "runNum").text = "0"
            ET.SubElement(single, "listType").text = str(entry.get("listType", 0))
            ET.SubElement(single, "plateNum").text = entry["plateNum"]
            # Emit an explicit empty element rather than self-closing
            card_elem = ET.SubElement(single, "cardNo")
            card_elem.text = entry.get("cardNo", "") or ""
            ET.SubElement(single, "startTime").text = entry.get("startTime", "0000-00-00T00:00:00Z")
            ET.SubElement(single, "endTime").text = entry.get("endTime", "0000-00-00T00:00:00Z")

        xml_body = ET.tostring(root, encoding="utf-8", method="xml")

        # 2) Send with proper Content-Type
        headers = {"Content-Type": "application/xml"}
        resp = requests.put(
            url,
            auth=HTTPDigestAuth(self.username, self.password),
            data=xml_body,
            headers=headers,
            timeout=self.timeout,
        )

        # 3) Parse result
        if resp.status_code == 200:
            return {"status": "success", "response": resp.text}
        else:
            # extract error details as before
            err = self._extract_error(resp.text)
            return {"status": "failed", "error": err}

    def delete_plate_from_list(self, plate_entries):
        """
        Изтрива един или повече регистрационни номера от списъка на камерата.

        Параметър:
          plate_entries: Списък от речници, където всеки трябва да съдържа:
            - 'plateNum': (str) Регистрационният номер, който да бъде изтрит.

        Изпраща DELETE заявка към: /ISAPI/ITC/Entrance/VCL

        XML структурата включва няколко <VCLDelCond> елемента, всеки със следните полета:
          - delVCLCond: Флаг за изтриване (стойност "1")
          - plateNum: Регистрационният номер
          - plateColor: Обикновено "0"
          - plateType: Обикновено "0"
          - cardNo: Повтаря регистрационния номер
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/VCL"
        root = ET.Element("VCLDelConditions")
        for entry in plate_entries:
            plate = entry.get('plateNum', '')
            cond = ET.Element("VCLDelCond")
            ET.SubElement(cond, "delVCLCond").text = "1"
            ET.SubElement(cond, "plateNum").text = plate
            ET.SubElement(cond, "plateColor").text = "0"
            ET.SubElement(cond, "plateType").text = "0"
            ET.SubElement(cond, "cardNo").text = plate
            root.append(cond)
        xml_body = ET.tostring(root, encoding="utf-8", method="xml")
        try:
            response = requests.delete(url, auth=HTTPDigestAuth(self.username, self.password), data=xml_body,
                                       timeout=self.timeout)
            if response.status_code == 200:
                _logger.debug("Hikvision delete_plate_from_list: Plates deleted successfully: %s", plate_entries)
                return {"status": "success", "response": response.text}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision delete_plate_from_list: FAILED with status %s. Error: %s",
                              response.status_code, error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision delete_plate_from_list: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def barrier_gate_control(self, operation, gate_num):
        """
        Управлява бариерната врата чрез изпращане на команда към камерата.

        Параметри:
          - operation: Стринг описание на операцията (например "on", "off", "stop", "locked")
          - gate_num: Номер на бариерата (int)

        Изпраща PUT заявка към: /ISAPI/ITC/Entrance/barrierGateCtrl

        XML структурата:
          <BarrierGateCtrl version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
              <barrietGateNum>{gate_num}</barrietGateNum>
              <BarrierGateCtrlList>
                  <barrietGateOper>{operation}</barrietGateOper>
              </BarrierGateCtrlList>
          </BarrierGateCtrl>
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/barrierGateCtrl"
        root = ET.Element("BarrierGateCtrl", version="2.0", xmlns="http://www.isapi.org/ver20/XMLSchema")
        ET.SubElement(root, "barrietGateNum").text = str(gate_num)
        barrier_list = ET.SubElement(root, "BarrierGateCtrlList")
        ET.SubElement(barrier_list, "barrietGateOper").text = operation
        xml_body = ET.tostring(root, encoding="utf-8", method="xml")
        try:
            response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password), data=xml_body,
                                    timeout=self.timeout)
            if response.status_code == 200:
                _logger.debug("Hikvision barrier_gate_control: Command '%s' executed successfully.", operation)
                return {"status": "success", "response": response.text}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision barrier_gate_control: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision barrier_gate_control: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def get_snapshot(self):
        """
        Извлича снимка от камерата.

        Използва GET заявка към: /ISAPI/Streaming/channels/1/picture

        Връща:
          - При успех: Речник със статус "success" и снимката, кодирана в base64 под ключа "snapshot_b64".
          - При грешка: Речник със статус "failed" и описание на грешката.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/Streaming/channels/1/picture"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            if response.status_code == 200:
                snapshot_b64 = base64.b64encode(response.content).decode('utf-8')
                _logger.debug("Hikvision get_snapshot: Snapshot retrieved and encoded in base64.")
                return {"status": "success", "snapshot_b64": snapshot_b64}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision get_snapshot: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision get_snapshot: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def get_plate_list(self, list_type='whitelist'):
        # Този метод не се използва поради съображения за сигурност.
        raise "Do not use. This method is not working for security reasons."

    def set_time_config(self, time_config):
        """
        Задава конфигурация на времето на камерата чрез /ISAPI/System/time.

        Параметър time_config трябва да е речник, съдържащ:
          - timeMode: Режим на синхронизация ("NTP" или "manual"). (Дефолт: "manual")
          - timeZone: Часова зона във формат "GMT+HH:MM" (напр. "GMT+02:00")
          - localTime: Локално време във формат ISO 8601 (напр. "2025-03-25T11:35:00+02:00")
          - NTP (опционално): Речник със следните ключове:
              - ipAddress: IP адрес на NTP сървъра.
              - syncInterval: Интервал за синхронизация.

        Изпраща PUT заявка към: /ISAPI/System/time

        Генерира XML със следната структура:
          <Time version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
            <timeMode>...</timeMode>
            <timeZone>...</timeZone>
            <localTime>...</localTime>          <!-- Ако е предоставено -->
            <NTP>
              <ipAddress>...</ipAddress>
              <syncInterval>...</syncInterval>
            </NTP>                              <!-- Ако има NTP данни -->
          </Time>
        """
        ns_uri = "http://www.isapi.org/ver20/XMLSchema"
        root = ET.Element("Time", {"version": "2.0", "xmlns": ns_uri})
        time_mode = time_config.get("timeMode", "manual")
        time_zone = time_config.get("timeZone", "GMT+00:00")
        local_time = time_config.get("localTime", "")
        ntp_info = time_config.get("NTP", {})

        tm = ET.SubElement(root, "timeMode")
        tm.text = time_mode

        tz = ET.SubElement(root, "timeZone")
        tz.text = time_zone

        if local_time:
            lt = ET.SubElement(root, "localTime")
            lt.text = local_time

        if ntp_info:
            ntp = ET.SubElement(root, "NTP")
            if "ipAddress" in ntp_info:
                ip = ET.SubElement(ntp, "ipAddress")
                ip.text = ntp_info["ipAddress"]
            if "syncInterval" in ntp_info:
                si = ET.SubElement(ntp, "syncInterval")
                si.text = str(ntp_info["syncInterval"])

        xml_body = ET.tostring(root, encoding="utf-8", method="xml")
        url = f"http://{self.ip_address}:{self.port}/ISAPI/System/time"
        try:
            response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password),
                                    data=xml_body, timeout=self.timeout)
            if response.status_code == 200:
                _logger.debug("Hikvision set_time_config: SUCCESS. Response: %s", response.text.strip())
                return {"status": "success", "response": response.text.strip()}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision set_time_config: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision set_time_config: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def get_time_config(self):
        """
        Извлича конфигурацията на времето от камерата чрез /ISAPI/System/time.

        Изпраща GET заявка към: /ISAPI/System/time

        Връща речник със следните ключове, ако е успешно:
          - status: "success"
          - timeMode: Режим на времето ("NTP" или "manual")
          - timeZone: Часова зона (например "GMT+02:00")
          - localTime: Локално време във формат ISO 8601

        При грешка връща статус "failed" с описание на грешката.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/System/time"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}
                timeMode = root.findtext('ns:timeMode', namespaces=ns)
                timeZone = root.findtext('ns:timeZone', namespaces=ns)
                localTime = root.findtext('ns:localTime', namespaces=ns)
                return {"status": "success", "timeMode": timeMode, "timeZone": timeZone, "localTime": localTime}
            else:
                error_detail = self._extract_error(response.text)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def get_dst_config(self):
        """
        Прочита DST (Daylight Saving Time) настройките на камерата.

        Прави GET заявка към: /ISAPI/System/time
        Очаква да намери <DST> блок в XML, примерно:
            <Time>
              ...
              <DST>
                <enabled>true</enabled>
                <mode>Offset</mode>
                <offset>60</offset>  <!-- минути -->
                <startTime>2025-03-31T02:00:00</startTime>
                <endTime>2025-10-30T03:00:00</endTime>
              </DST>
            </Time>

        Възможно е при някои фърмуери да има различен формат или изобщо да няма <DST> елемент.

        Връща речник със статус и намерените DST полета. Ако не намери DST блок, приема, че е изключен.
        Примерен връщан резултат:
            {
              "status": "success",
              "dst_enabled": True,
              "dst_mode": "Offset",
              "dst_offset_minutes": 60,
              "dst_start": "2025-03-31T02:00:00",
              "dst_end": "2025-10-30T03:00:00"
            }
        Или при грешка:
            {
              "status": "failed",
              "error": "описание на грешката"
            }
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/System/time"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            if response.status_code != 200:
                error_detail = self._extract_error(response.text)
                return {"status": "failed", "error": error_detail}

            root = ET.fromstring(response.content)
            ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}

            dst_elem = root.find('ns:DST', namespaces=ns)
            if dst_elem is None:
                # Приема, че DST не е налично или е изключено
                return {
                    "status": "success",
                    "dst_enabled": False,
                    "dst_mode": None,
                    "dst_offset_minutes": 0,
                    "dst_start": None,
                    "dst_end": None
                }

            # Четем детайлите в <DST> блока
            enabled_text = dst_elem.findtext('ns:enabled', default='false', namespaces=ns).lower()
            mode = dst_elem.findtext('ns:mode', default='', namespaces=ns)
            offset_str = dst_elem.findtext('ns:offset', default='0', namespaces=ns)
            start_time = dst_elem.findtext('ns:startTime', default='', namespaces=ns)
            end_time = dst_elem.findtext('ns:endTime', default='', namespaces=ns)

            return {
                "status": "success",
                "dst_enabled": (enabled_text == 'true'),
                "dst_mode": mode,
                "dst_offset_minutes": int(offset_str),
                "dst_start": start_time,
                "dst_end": end_time
            }

        except Exception as e:
            _logger.error("Error reading DST config: %s", e)
            return {"status": "failed", "error": str(e)}

    def set_dst_config(self, enable=False, mode="Offset", offset_minutes=60,
                       start_time="2025-03-31T02:00:00", end_time="2025-10-30T03:00:00"):
        """
        Активира/деактивира DST (Daylight Saving Time) в камерата.

        Параметри:
          - enable (bool): True, ако искаме да включим DST; False, за да го изключим.
          - mode (str): Тип режим на DST (обикновено "Offset" или "Recurring").
                       При някои фърмуери може да е "Manual" или друго.
          - offset_minutes (int): Колко минути да се добавят при DST (60 = +1 час).
          - start_time (str): Начална дата/час за DST (ISO 8601).
          - end_time (str): Крайна дата/час за DST (ISO 8601).

        Примерен XML (ако enable=True):
            <Time version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
              <DST>
                <enabled>true</enabled>
                <mode>Offset</mode>
                <offset>60</offset>
                <startTime>2025-03-31T02:00:00</startTime>
                <endTime>2025-10-30T03:00:00</endTime>
              </DST>
            </Time>
        Ако enable=False, може да изпратим:
            <Time>
              <DST>
                <enabled>false</enabled>
              </DST>
            </Time>
        или напълно да премахнем DST блока.

        Забележка: Някои камери изискват да подадем и останалите полета като <timeMode>, <timeZone> и т.н.
        Често е нужно да прочетем текущата конфигурация през get_time_config(), да модифицираме DST частта
        и после да изпратим обратно целия XML. Тук, за простота, се изпраща само DST блокът.
        Ако фърмуерът изисква пълен XML, комбинирайте този код с логиката от set_time_config().
        """
        ns_uri = "http://www.isapi.org/ver20/XMLSchema"
        # Създаваме <Time> корен
        root = ET.Element("Time", {"version": "2.0", "xmlns": ns_uri})

        # Създаваме <DST> блок
        dst_elem = ET.SubElement(root, "DST")
        ET.SubElement(dst_elem, "enabled").text = "true" if enable else "false"

        if enable:
            # Ако DST е включено, задаваме останалите полета
            ET.SubElement(dst_elem, "mode").text = mode
            ET.SubElement(dst_elem, "offset").text = str(offset_minutes)
            ET.SubElement(dst_elem, "startTime").text = start_time
            ET.SubElement(dst_elem, "endTime").text = end_time

        xml_body = ET.tostring(root, encoding="utf-8", method="xml")
        url = f"http://{self.ip_address}:{self.port}/ISAPI/System/time"
        try:
            response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password),
                                    data=xml_body, timeout=self.timeout)
            if response.status_code == 200:
                _logger.debug("Hikvision set_dst_config: SUCCESS. Response: %s", response.text.strip())
                return {"status": "success", "response": response.text.strip()}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision set_dst_config: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision set_dst_config: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    def get_entrance_param(self):
        """
        Извлича конфигурацията на Entrance параметрите.
        Използва GET заявка към: /ISAPI/ITC/Entrance/entranceParam
        Връща речник с парсирана информация.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/entranceParam"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            if response.status_code == 200:
                ns = {'ns': 'http://www.hikvision.com/ver10/XMLSchema'}
                root = ET.fromstring(response.content)
                entrance = root.find('ns:EntranceParam', namespaces=ns)
                if entrance is None:
                    return {"status": "failed", "error": "Не е намерен елемент EntranceParam"}
                result = {
                    "laneNum": entrance.findtext("ns:laneNum", namespaces=ns),
                    "bEnable": entrance.findtext("ns:bEnable", namespaces=ns),
                    "ctrlMode": entrance.findtext("ns:ctrlMode", namespaces=ns),
                    "relateTriggerMode": entrance.findtext("ns:relateTriggerMode", namespaces=ns)
                }
                # vehControlMeasure
                vcm = entrance.find("ns:vehControlMeasure", namespaces=ns)
                if vcm is not None:
                    result["vehControlMeasure"] = {
                        "plateNumFuzzyEnabled": vcm.findtext("ns:plateNumFuzzyEnabled", namespaces=ns),
                        "plateNumOnlyEnable": vcm.findtext("ns:plateNumOnlyEnable", namespaces=ns),
                        "plateNumColorEnable": vcm.findtext("ns:plateNumColorEnable", namespaces=ns),
                        "personVerificationType": vcm.findtext("ns:personVerificationType", namespaces=ns)
                    }
                # vehInfoManagList
                vim_list = []
                vim_elem = entrance.find("ns:vehInfoManagList", namespaces=ns)
                if vim_elem is not None:
                    for veh in vim_elem.findall("ns:vehInfoManag", namespaces=ns):
                        vim_list.append({
                            "vehInfoManagNum": veh.findtext("ns:vehInfoManagNum", namespaces=ns),
                            "barrierGateOper": veh.findtext("ns:barrierGateOper", namespaces=ns),
                            "relayOutAlarmEnable": veh.findtext("ns:relayOutAlarmEnable", namespaces=ns),
                            "upAlarmEnable": veh.findtext("ns:upAlarmEnable", namespaces=ns),
                            "hostUpAlarmEnable": veh.findtext("ns:hostUpAlarmEnable", namespaces=ns),
                            "emailAlarmEnable": veh.findtext("ns:emailAlarmEnable", namespaces=ns)
                        })
                    result["vehInfoManagList"] = vim_list
                # relayList
                relay_list = []
                rl_elem = entrance.find("ns:relayList", namespaces=ns)
                if rl_elem is not None:
                    for relay in rl_elem.findall("ns:relay", namespaces=ns):
                        relay_list.append({
                            "relayNum": relay.findtext("ns:relayNum", namespaces=ns),
                            "relayFunction": relay.findtext("ns:relayFunction", namespaces=ns),
                            "relayOutTime": relay.findtext("ns:relayOutTime", namespaces=ns)
                        })
                    result["relayList"] = relay_list
                # IOAlarmList
                io_list = []
                io_elem = entrance.find("ns:IOAlarmList", namespaces=ns)
                if io_elem is not None:
                    for io in io_elem.findall("ns:IOAlarm", namespaces=ns):
                        io_list.append({
                            "IOAlarmNum": io.findtext("ns:IOAlarmNum", namespaces=ns),
                            "IOAlarmType": io.findtext("ns:IOAlarmType", namespaces=ns)
                        })
                    result["IOAlarmList"] = io_list
                # останали елементи
                result["notCloseCarFollow"] = entrance.findtext("ns:notCloseCarFollow", namespaces=ns)
                bck_elem = entrance.find("ns:bigCarKeepOpen", namespaces=ns)
                if bck_elem is not None:
                    result["bigCarKeepOpen"] = {
                        "enabled": bck_elem.findtext("ns:enabled", namespaces=ns),
                        "duration": bck_elem.findtext("ns:duration", namespaces=ns)
                    }
                pd_elem = entrance.find("ns:ParkingDetection", namespaces=ns)
                if pd_elem is not None:
                    result["ParkingDetection"] = {
                        "enabled": pd_elem.findtext("ns:enabled", namespaces=ns),
                        "judgeTime": pd_elem.findtext("ns:judgeTime", namespaces=ns)
                    }
                msm_elem = entrance.find("ns:MasterSlaveMode", namespaces=ns)
                if msm_elem is not None:
                    result["MasterSlaveMode"] = {
                        "enabled": msm_elem.findtext("ns:enabled", namespaces=ns),
                        "Ipv4Address": msm_elem.findtext("ns:Ipv4Address", namespaces=ns),
                        "portNo": msm_elem.findtext("ns:portNo", namespaces=ns),
                        "username": msm_elem.findtext("ns:username", namespaces=ns),
                        "uploadMode": msm_elem.findtext("ns:uploadMode", namespaces=ns),
                        "uploadWaitTime": msm_elem.findtext("ns:uploadWaitTime", namespaces=ns),
                        "plateNumTolerantEnabled": msm_elem.findtext("ns:plateNumTolerantEnabled", namespaces=ns),
                        "triggerSnapEnabled": msm_elem.findtext("ns:triggerSnapEnabled", namespaces=ns),
                        "password": msm_elem.findtext("ns:password", namespaces=ns)
                    }
                return {"status": "success", "response": result}
            else:
                error_detail = self._extract_error(response.text)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def set_entrance_param(self, config):
        """
        Задава Entrance параметрите.
        Параметър config трябва да е речник със структура, съответстваща на EntranceParamList.
        Използва PUT заявка към: /ISAPI/ITC/Entrance/entranceParam
        """
        # Създаваме основния XML елемент
        root = ET.Element("EntranceParamList", xmlns="http://www.hikvision.com/ver10/XMLSchema", version="1.0")
        entrance = ET.SubElement(root, "EntranceParam")
        # Основни полета
        for field in ["laneNum", "bEnable", "ctrlMode", "relateTriggerMode"]:
            if field in config:
                ET.SubElement(entrance, field).text = str(config[field])
        # vehControlMeasure
        vcm = config.get("vehControlMeasure", {})
        if vcm:
            vcm_elem = ET.SubElement(entrance, "vehControlMeasure")
            for field in ["plateNumFuzzyEnabled", "plateNumOnlyEnable", "plateNumColorEnable",
                          "personVerificationType"]:
                if field in vcm:
                    ET.SubElement(vcm_elem, field).text = str(vcm[field])
        # vehInfoManagList
        vim_list = config.get("vehInfoManagList", [])
        if vim_list:
            vim_elem = ET.SubElement(entrance, "vehInfoManagList")
            for veh in vim_list:
                veh_elem = ET.SubElement(vim_elem, "vehInfoManag")
                for field in ["vehInfoManagNum", "barrierGateOper", "relayOutAlarmEnable", "upAlarmEnable",
                              "hostUpAlarmEnable", "emailAlarmEnable"]:
                    if field in veh:
                        ET.SubElement(veh_elem, field).text = str(veh[field])
        # relayList
        relays = config.get("relayList", [])
        if relays:
            relay_list_elem = ET.SubElement(entrance, "relayList")
            for relay in relays:
                relay_elem = ET.SubElement(relay_list_elem, "relay")
                for field in ["relayNum", "relayFunction", "relayOutTime"]:
                    if field in relay:
                        ET.SubElement(relay_elem, field).text = str(relay[field])
        # IOAlarmList
        ioalarms = config.get("IOAlarmList", [])
        if ioalarms:
            io_elem = ET.SubElement(entrance, "IOAlarmList")
            for io in ioalarms:
                io_alarm = ET.SubElement(io_elem, "IOAlarm")
                for field in ["IOAlarmNum", "IOAlarmType"]:
                    if field in io:
                        ET.SubElement(io_alarm, field).text = str(io[field])
        # Останали полета
        if "notCloseCarFollow" in config:
            ET.SubElement(entrance, "notCloseCarFollow").text = str(config["notCloseCarFollow"]).lower()
        if "bigCarKeepOpen" in config:
            bcko = ET.SubElement(entrance, "bigCarKeepOpen")
            for field in ["enabled", "duration"]:
                if field in config["bigCarKeepOpen"]:
                    value = config["bigCarKeepOpen"][field]
                    bcko.text = ""  # placeholder
                    ET.SubElement(bcko, field).text = str(value).lower() if isinstance(value, bool) else str(value)
        if "ParkingDetection" in config:
            pd = ET.SubElement(entrance, "ParkingDetection")
            for field in ["enabled", "judgeTime"]:
                if field in config["ParkingDetection"]:
                    value = config["ParkingDetection"][field]
                    ET.SubElement(pd, field).text = str(value).lower() if isinstance(value, bool) else str(value)
        if "MasterSlaveMode" in config:
            msm = ET.SubElement(entrance, "MasterSlaveMode")
            for field in ["enabled", "Ipv4Address", "portNo", "username", "uploadMode", "uploadWaitTime",
                          "plateNumTolerantEnabled", "triggerSnapEnabled", "password"]:
                if field in config["MasterSlaveMode"]:
                    value = config["MasterSlaveMode"][field]
                    ET.SubElement(msm, field).text = str(value).lower() if isinstance(value, bool) else str(value)

        xml_body = ET.tostring(root, encoding="utf-8", method="xml")
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/entranceParam"
        try:
            response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password),
                                    data=xml_body, timeout=self.timeout)
            if response.status_code == 200:
                return {"status": "success", "response": response.text}
            else:
                error_detail = self._extract_error(response.text)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            return {"status": "failed", "error": str(e)}


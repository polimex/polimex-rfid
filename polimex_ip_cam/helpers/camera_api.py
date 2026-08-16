import requests
import xml.etree.ElementTree as ET          # building OUR requests (trusted, namespace-registered)
from datetime import datetime
from requests.auth import HTTPDigestAuth
import logging
import base64
import json

import pytz

from lxml import etree

from odoo.addons.polimex_ip_cam.helpers.safe_xml import (
    parse_untrusted_xml,          # read-only parsing of camera responses
    parse_untrusted_xml_stdlib,   # read-modify-write trees that re-serialise via stdlib ET
)

_logger = logging.getLogger(__name__)

# ISAPI ver20 namespace used by the HttpHostNotification messages. Registering
# it as the default (empty) prefix makes ElementTree re-serialise parsed or
# qualified trees with a plain `xmlns="..."` on the root instead of `ns0:`
# prefixes — which is what the camera expects on the wire.
ISAPI_VER20_NS = "http://www.isapi.org/ver20/XMLSchema"
ET.register_namespace("", ISAPI_VER20_NS)

# Heartbeat (SubscribeEvent keep-alive, seconds). Cameras advertise their own
# [min, max] range via the httpHosts/capabilities endpoint; these are only used
# as a safe default and as a conservative ceiling when that range cannot be read
# (a value above the camera's max is rejected with "Invalid XML Content").
DEFAULT_HEARTBEAT = 30
FALLBACK_MAX_HEARTBEAT = 180

# Plate white/black list management. Legacy cameras use /ISAPI/ITC/Entrance/VCL;
# TCG/7-series firmware (e.g. DS-TCG406-E V5.4.4 / V5.5.0) dropped VCL and manage
# the list via the LP-audit API on the Traffic channel below: a JSON record
# upsert (licensePlateAuditData/record?format=json) plus a JSON delete
# (DelLicensePlateAuditData). The JSON record body and field set were confirmed
# against a live camera's web-UI traffic (V5.5.0.100228).
LP_AUDIT_CHANNEL = 1
# Odoo numeric listType ('0'/'1') -> the camera's JSON record listType wording.
# NB: the WRITE path (record upsert) uses 'allowList'/'blockList', but the READ
# path (searchLPListAudit) reports the bucket in a <type> element with DIFFERENT
# wording: 'whiteList'/'blackList' (camelCase). Keep both mappings so a reconcile
# can line the device state up against the Odoo list_category.
LP_RECORD_LISTTYPE = {"0": "allowList", "1": "blockList"}
LP_READ_TYPE_TO_CATEGORY = {"whiteList": "whitelist", "blackList": "blacklist"}
# Permanent-validity window used when a plate carries no explicit start/end.
# In the JSON record these map to createTime (start) and effectiveTime (end);
# the camera requires a non-empty effectiveTime.
LP_DEFAULT_START_TIME = "2000-01-01T00:00:00"
LP_DEFAULT_END_TIME = "2099-12-31T23:59:59"
# The record shapes the write ladder can fall back through, best first.
# 'full' is the live-validated field set; 'no_card' blanks the linked card
# number; 'no_times' drops the validity window back to the permanent
# defaults. Each step trades one OPTIONAL detail for the plate itself
# arriving - the access decision is taken by the Odoo lists on every event,
# so a camera-side record without a card number or a window still admits
# and refuses exactly the same cars.
LP_RECORD_SHAPES = ('full', 'no_card', 'no_times')


def _ver20_tag(tag):
    """Qualify a local tag name with the ISAPI ver20 namespace."""
    return "{%s}%s" % (ISAPI_VER20_NS, tag)

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

    def __init__(self, ip_address, port, username, password, timeout=5,
                 tz=None, record_shape='full'):
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        #: The camera's own time zone. Validity windows arrive here in UTC
        #: (Odoo stores them so), but the camera compares them against ITS
        #: wall clock - a window sent verbatim is off by the zone offset.
        self.tz = tz
        #: The record shape this camera is known to accept ('full', 'no_card',
        #: 'no_times'). Discovered by the write ladder and persisted by the
        #: caller, so the second and every later record skips the shapes the
        #: firmware already refused.
        self.record_shape = record_shape if record_shape in LP_RECORD_SHAPES else 'full'

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
            root = parse_untrusted_xml(response_text)
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
                    root = parse_untrusted_xml(response.text)
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
                    # Reachable + authenticated, but the body is not the expected
                    # ISAPI XML (wrong model/firmware, or a captive page).
                    _logger.debug("Hikvision check_connection: XML parsing error: %s", e)
                    return {"status": "protocol_error", "error": str(e)}
            else:
                error_detail = self._extract_error(response.text)
                _logger.debug("Hikvision check_connection: HTTP %s. %s", response.status_code, error_detail)
                # 401/403 = wrong credentials / no rights; anything else = some
                # other camera-side error. The caller (model) owns operator-level
                # logging, gated on state change, to avoid per-poll log spam.
                status = "auth_failed" if response.status_code in (401, 403) else "error"
                return {"status": status, "error": error_detail}
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # DNS/route/connect/timeout -> the camera is not reachable at all.
            _logger.debug("Hikvision check_connection: unreachable: %s", e)
            return {"status": "unreachable", "error": str(e)}
        except Exception as e:
            _logger.debug("Hikvision check_connection: request error: %s", e)
            return {"status": "error", "error": str(e)}

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
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            if response.status_code == 200:
                xml_response = response.text.strip()
                root = parse_untrusted_xml(xml_response)
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
                    'checkResponseEnabled': root.findtext('ns:checkResponseEnabled', namespaces=ns),
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
        # Determine the camera's allowed heartbeat range and clamp the desired
        # value into it. A heartbeat above the camera's advertised max is
        # rejected with "Invalid XML Content" (statusCode 6).
        caps = self.get_http_host_capabilities()
        if caps.get("status") == "success":
            hb_min = caps["heartbeat"]["min"]
            hb_max = caps["heartbeat"]["max"]
        else:
            hb_min, hb_max = 0, FALLBACK_MAX_HEARTBEAT
            _logger.warning(
                "Hikvision set_http_host: heartbeat capabilities unavailable (%s); "
                "applying conservative range [0, %s].",
                caps.get("error"), FALLBACK_MAX_HEARTBEAT)

        subscribe = config.get("SubscribeEvent", {})
        heartbeat = str(self._clamp_heartbeat(subscribe.get("heartbeat"), hb_min, hb_max))
        anpr = config.get("ANPR", {})

        # Read-modify-write: start from the camera's current document so its own
        # element ordering and any fields we do not manage (e.g.
        # checkResponseEnabled) survive untouched. Fall back to building a fresh
        # document if the GET fails — the camera accepts that document too, it
        # just cannot carry forward the unmanaged fields.
        root = self._fetch_current_http_host_tree()
        if root is None:
            root = ET.Element(_ver20_tag("HttpHostNotification"), version="2.0")

        self._set_child(root, "id", config.get("id", "1"))
        self._set_child(root, "url", config.get("url", "/ipcam/anpr/event"))
        self._set_child(root, "protocolType", config.get("protocolType", "HTTP"))
        self._set_child(root, "parameterFormatType", config.get("parameterFormatType", "XML"))
        self._set_child(root, "addressingFormatType", config.get("addressingFormatType", "ipaddress"))
        self._set_child(root, "ipAddress", config.get("ipAddress", ""))
        self._set_child(root, "portNo", config.get("portNo", ""))
        self._set_child(root, "userName", config.get("userName", ""))
        self._set_child(root, "httpAuthenticationMethod", config.get("httpAuthenticationMethod", "none"))

        # ANPR block — which image type to upload.
        anpr_elem = self._get_or_create_child(root, "ANPR")
        self._set_child(anpr_elem, "detectionUpLoadPicturesType",
                        anpr.get("detectionUpLoadPicturesType", "all"))

        # SubscribeEvent block — event subscription + clamped heartbeat.
        subscribe_elem = self._get_or_create_child(root, "SubscribeEvent")
        self._set_child(subscribe_elem, "heartbeat", heartbeat)
        self._set_child(subscribe_elem, "eventMode", subscribe.get("eventMode", "all"))

        # Only write checkResponseEnabled when the caller explicitly provides one
        # (e.g. read back from the camera into server_setup); never invent a
        # default. When absent, the read-modify-write above keeps the camera's
        # own value (merge mode) or omits it (rebuild fallback).
        check_response = config.get("checkResponseEnabled")
        if check_response not in (None, ""):
            self._set_child(root, "checkResponseEnabled", check_response)

        self._set_child(root, "enabled", config.get("enabled", "false"))

        xml_body = ET.tostring(root, encoding="utf-8", method="xml")

        try:
            response = requests.put(
                f"http://{self.ip_address}:{self.port}/ISAPI/Event/notification/httpHosts/1",
                auth=HTTPDigestAuth(self.username, self.password),
                data=xml_body,
                timeout=self.timeout
            )
            if response.status_code == 200:
                _logger.debug("Hikvision set_http_host: SUCCESS (heartbeat=%s). Response: %s",
                              heartbeat, response.text.strip())
                return {"status": "success", "response": response.text.strip()}
            else:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision set_http_host: FAILED with status %s. Error: %s", response.status_code,
                              error_detail)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision set_http_host: Request error: %s", e)
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def _clamp_heartbeat(value, min_v, max_v):
        """Clamp a desired heartbeat (seconds) into the camera's [min, max].

        A non-numeric or missing value collapses to DEFAULT_HEARTBEAT, which is
        then clamped as well (the camera's min may exceed the default).
        """
        try:
            hb = int(value)
        except (TypeError, ValueError):
            hb = DEFAULT_HEARTBEAT
        return max(min_v, min(hb, max_v))

    @staticmethod
    def _parse_heartbeat_capabilities(xml_text):
        """Parse the httpHosts/capabilities document for the heartbeat range.

        Returns ``{"min": int, "max": int}`` or ``None`` when the element or its
        min/max attributes are missing/unparseable.
        """
        try:
            root = parse_untrusted_xml(xml_text)
        except etree.XMLSyntaxError:
            return None
        hb = root.find(".//" + _ver20_tag("heartbeat"))
        if hb is None:
            # Tolerate firmwares that omit the namespace on capabilities.
            hb = root.find(".//heartbeat")
        if hb is None:
            return None
        min_attr, max_attr = hb.get("min"), hb.get("max")
        if min_attr is None or max_attr is None:
            return None
        try:
            return {"min": int(min_attr), "max": int(max_attr)}
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _set_child(parent, tag, text):
        """Upsert a ver20-namespaced child element under ``parent``.

        Reuses an existing element (preserving the document's element order) or
        appends a new one, then sets its text.
        """
        child = HikvisionCamera._get_or_create_child(parent, tag)
        child.text = "" if text is None else str(text)
        return child

    @staticmethod
    def _get_or_create_child(parent, tag):
        """Return the ver20-namespaced child ``tag``, creating it if absent."""
        qtag = _ver20_tag(tag)
        child = parent.find(qtag)
        if child is None:
            child = ET.SubElement(parent, qtag)
        return child

    def get_http_host_capabilities(self):
        """Read the allowed HTTP-host configuration ranges from the camera.

        GET /ISAPI/Event/notification/httpHosts/capabilities and extract the
        SubscribeEvent heartbeat ``[min, max]``. Returns
        ``{"status": "success", "heartbeat": {"min": int, "max": int}}`` or a
        ``{"status": "failed", "error": ...}`` dict the caller can fall back on.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/Event/notification/httpHosts/capabilities"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password),
                                    timeout=self.timeout)
        except Exception as e:
            _logger.warning("Hikvision get_http_host_capabilities: request error: %s", e, exc_info=True)
            return {"status": "failed", "error": str(e)}
        if response.status_code != 200:
            error_detail = self._extract_error(response.text)
            _logger.warning("Hikvision get_http_host_capabilities: HTTP %s. Error: %s",
                            response.status_code, error_detail)
            return {"status": "failed", "error": error_detail}
        heartbeat = self._parse_heartbeat_capabilities(response.text)
        if not heartbeat:
            _logger.warning("Hikvision get_http_host_capabilities: no usable <heartbeat min/max> advertised")
            return {"status": "failed", "error": "heartbeat range not advertised"}
        return {"status": "success", "heartbeat": heartbeat}

    def _fetch_current_http_host_tree(self):
        """Return the camera's current httpHosts/1 document as an Element.

        Returns ``None`` (and logs a warning) when the document cannot be read or
        parsed, so the caller falls back to building a fresh document.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/Event/notification/httpHosts/1"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password),
                                    timeout=self.timeout)
        except Exception as e:
            _logger.warning("Hikvision set_http_host: could not read current config for merge: %s",
                            e, exc_info=True)
            return None
        if response.status_code != 200:
            _logger.warning("Hikvision set_http_host: current config GET returned HTTP %s; "
                            "rebuilding the document from scratch.", response.status_code)
            return None
        try:
            return parse_untrusted_xml_stdlib(response.text)
        except (ET.ParseError, etree.XMLSyntaxError) as e:
            _logger.warning("Hikvision set_http_host: current config XML unparseable (%s); "
                            "rebuilding the document from scratch.", e)
            return None

    def _uses_lp_audit_api(self):
        """True when this camera manages the plate list via the newer LP-audit
        API (Traffic channel) rather than the legacy VCL endpoint.

        Detected once (and cached on the instance) by probing the VCL
        capabilities: VCL-capable cameras answer HTTP 200; TCG/7-series
        firmware that dropped VCL answer statusCode 4 "notSupport".
        """
        if getattr(self, "_lp_audit_api", None) is not None:
            return self._lp_audit_api
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/VCL/capabilities"
        try:
            resp = requests.get(url, auth=HTTPDigestAuth(self.username, self.password),
                                timeout=self.timeout)
            # Cache only a conclusive answer.
            self._lp_audit_api = resp.status_code != 200
            return self._lp_audit_api
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            # The camera is unreachable right now - a network condition the
            # message states in full. The traceback added two screens of
            # noise per probe on a live site while saying nothing more.
            _logger.warning("Hikvision plate-list capability probe: camera "
                            "unreachable (%s); assuming LP-audit API for this "
                            "operation.", e)
            return True
        except Exception as e:
            # Probe unreachable — assume the modern API (the deployed TCG
            # cameras) for THIS call and let the actual operation surface the
            # error, but do NOT cache so a transient blip can't pin the instance.
            _logger.warning("Hikvision plate-list capability probe failed (%s); "
                            "assuming LP-audit API for this operation.", e, exc_info=True)
            return True

    def add_plate_to_list(self, plate_entries):
        """Add/update one or more plates on the camera's white/black list.

        Routes to the camera's supported API: legacy VCL (SetVCLData) or, on
        TCG/7-series firmware that dropped VCL, the LP-audit JSON record upsert.
        Entry dict keys: plateNum, listType ('0' whitelist / '1' blacklist),
        optional cardNo, startTime, endTime.
        """
        if self._uses_lp_audit_api():
            return self._lp_audit_add(plate_entries)
        return self._vcl_add(plate_entries)

    def _lp_time(self, value):
        """A validity moment in the camera's own wall clock, no zone suffix.

        The live-validated record format carries plain local times
        ('2000-01-01T00:00:00'); the values arriving here are Odoo's, in UTC
        and often 'Z'-suffixed. Sent verbatim they are doubly wrong: a suffix
        the firmware may refuse outright, and a window shifted by the zone
        offset even where it does not. Unparseable values pass through
        untouched - refusing them is the camera's call, not ours.
        """
        if not value:
            return None
        text = str(value).strip()
        try:
            moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            return text
        if moment.tzinfo is not None:
            try:
                zone = pytz.timezone(self.tz) if self.tz else pytz.UTC
            except pytz.UnknownTimeZoneError:
                zone = pytz.UTC
            moment = moment.astimezone(zone).replace(tzinfo=None)
        return moment.strftime('%Y-%m-%dT%H:%M:%S')

    def _lp_record_info(self, entry, shape='full'):
        """Build one LicensePlateInfoList element for the JSON record upsert,
        mirroring the field set the camera web UI sends. Optional fields are
        passed as empty strings (the firmware rejects a record with keys
        omitted); the validity window maps to createTime (start) /
        effectiveTime (end), defaulting to a permanent window.

        ``shape`` degrades the OPTIONAL content only - 'no_card' blanks the
        linked card number, 'no_times' falls back to the permanent window.
        The plate and the bucket always travel in full.
        """
        plate = entry.get("plateNum", "")
        card_no = entry.get("cardNo", "") or ""
        if shape != 'full':
            card_no = ""
        start = self._lp_time(entry.get("startTime"))
        end = self._lp_time(entry.get("endTime"))
        if shape == 'no_times':
            start = end = None
        return {
            "id": plate,
            "LicensePlate": plate,
            "listType": LP_RECORD_LISTTYPE.get(str(entry.get("listType", "0")), "allowList"),
            "cardNo": card_no,
            "cardID": card_no,
            "plateType": "",
            "plateColor": "",
            "plateDescription": "",
            "remoteControllerCode": "",
            "plateNoSub": "",
            "CRIndex": "",
            "area": "",
            "name": "",
            "certificateType": "",
            "certificateNumber": "",
            "operationType": "add",
            "virtualParkingNum": "",
            "groupName": "",
            "createTime": start or LP_DEFAULT_START_TIME,
            "effectiveTime": end or LP_DEFAULT_END_TIME,
            "operation": "new",
        }

    @staticmethod
    def _lp_audit_json_ok(response):
        """An LP-audit JSON endpoint reports success as HTTP 200 + statusCode 1.
        Returns True only when both hold."""
        if response.status_code != 200:
            return False
        try:
            return json.loads(response.text or "{}").get("statusCode") == 1
        except ValueError:
            return False

    def _lp_audit_add(self, plate_entries):
        """JSON record upsert, walking the shape ladder when refused.

        A firmware that rejects one OPTIONAL detail of the record (a linked
        card number, a validity window) used to cost the plate itself: the
        refusal read as a per-record failure and a thousand-plate reload
        produced a thousand identical errors while the list stayed empty.
        The ladder retries the same plates with that detail withdrawn, and
        the accepted shape is reported back so the caller can persist it -
        the next record then starts straight at what this camera speaks.
        """
        url = (f"http://{self.ip_address}:{self.port}"
               f"/ISAPI/Traffic/channels/{LP_AUDIT_CHANNEL}/licensePlateAuditData/record?format=json")
        shapes = LP_RECORD_SHAPES[LP_RECORD_SHAPES.index(self.record_shape):]
        last_error, last_status = None, None
        replaced = False
        for shape in shapes:
            payload = {"LicensePlateInfoList":
                       [self._lp_record_info(e, shape) for e in plate_entries]}
            try:
                response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password),
                                        headers={"Content-Type": "application/json"},
                                        data=json.dumps(payload), timeout=self.timeout)
            except Exception as e:
                _logger.error("Hikvision LP-audit record upsert: Request error: %s",
                              e, exc_info=True)
                return {"status": "failed", "error": str(e)}
            if self._lp_audit_json_ok(response):
                if shape != shapes[0]:
                    _logger.warning(
                        "Hikvision LP-audit: the camera refused the '%s' record "
                        "shape and accepted '%s' - remembering it so later "
                        "records go straight through. Last refusal: %s",
                        shapes[0], shape, last_error)
                _logger.debug("Hikvision LP-audit record upsert OK (%s): %s",
                              shape, [e.get("plateNum") for e in plate_entries])
                return {"status": "success", "response": response.text,
                        "shape_used": shape, "replaced": replaced}
            last_error = self._extract_error(response.text)
            last_status = response.status_code
            if not replaced:
                # The plate may already LIVE on the camera - these lists
                # survive from the previous system, and this firmware refuses
                # an upsert onto an existing plate as badParameters while
                # accepting a fresh one (a self-test's clean test plate goes
                # through, every real plate does not). Withdraw exactly this
                # plate and try the same shape once more: replace, not guess.
                self._lp_audit_delete(plate_entries)
                replaced = True
                try:
                    response = requests.put(
                        url, auth=HTTPDigestAuth(self.username, self.password),
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(payload), timeout=self.timeout)
                except Exception as e:
                    _logger.error("Hikvision LP-audit record upsert: Request "
                                  "error: %s", e, exc_info=True)
                    return {"status": "failed", "error": str(e)}
                if self._lp_audit_json_ok(response):
                    _logger.info(
                        "Hikvision LP-audit: %s existing record(s) replaced - "
                        "the camera refuses an upsert onto a plate it already "
                        "holds.", [e.get("plateNum") for e in plate_entries])
                    return {"status": "success", "response": response.text,
                            "shape_used": shape, "replaced": True}
                last_error = self._extract_error(response.text)
                last_status = response.status_code
        _logger.error("Hikvision LP-audit record upsert FAILED (HTTP %s) in every "
                      "record shape. Error: %s", last_status, last_error)
        return {"status": "failed", "error": last_error}

    def _vcl_add(self, plate_entries):
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/VCL"
        set_vcl_data = ET.Element("SetVCLData")
        vcl_data_list = ET.SubElement(set_vcl_data, "VCLDataList")
        for entry in plate_entries:
            single_entry = ET.Element("singleVCLData")
            ET.SubElement(single_entry, "id").text = "0"
            ET.SubElement(single_entry, "runNum").text = "0"
            ET.SubElement(single_entry, "listType").text = str(entry.get('listType', '0'))
            ET.SubElement(single_entry, "plateNum").text = entry.get('plateNum', '')
            ET.SubElement(single_entry, "cardNo").text = entry.get('cardNo', '')
            ET.SubElement(single_entry, "startTime").text = entry.get('startTime', "0000-00-00T00:00:00Z")
            ET.SubElement(single_entry, "endTime").text = entry.get('endTime', "0000-00-00T00:00:00Z")
            vcl_data_list.append(single_entry)
        xml_body = ET.tostring(set_vcl_data, encoding="utf-8", method="xml")
        try:
            response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password), data=xml_body,
                                    timeout=self.timeout)
            if response.status_code == 200:
                _logger.debug("Hikvision add_plate_to_list (VCL): added: %s", plate_entries)
                return {"status": "success", "response": response.text}
            error_detail = self._extract_error(response.text)
            _logger.error("Hikvision add_plate_to_list (VCL): FAILED with status %s. Error: %s",
                          response.status_code, error_detail)
            return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision add_plate_to_list (VCL): Request error: %s", e, exc_info=True)
            return {"status": "failed", "error": str(e)}

    def delete_plate_from_list(self, plate_entries):
        """Remove one or more plates. Routes to the LP-audit JSON delete
        (DelLicensePlateAuditData) or the legacy VCL delete (VCLDelCond).
        Entry dict requires 'plateNum'."""
        if self._uses_lp_audit_api():
            return self._lp_audit_delete(plate_entries)
        return self._vcl_delete(plate_entries)

    def _lp_audit_delete(self, plate_entries):
        url = (f"http://{self.ip_address}:{self.port}"
               f"/ISAPI/Traffic/channels/{LP_AUDIT_CHANNEL}/DelLicensePlateAuditData?format=json")
        errors = []
        for entry in plate_entries:
            plate = entry.get('plateNum', '')
            payload = {"deleteAllEnabled": False,
                       "CompoundCond": {"plateColor": "", "licensePlate": plate}}
            try:
                response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password),
                                        headers={"Content-Type": "application/json"},
                                        data=json.dumps(payload), timeout=self.timeout)
                if not self._lp_audit_json_ok(response):
                    errors.append("%s: HTTP %s %s" % (plate, response.status_code, (response.text or "")[:120]))
            except Exception as e:
                errors.append("%s: %s" % (plate, e))
        if errors:
            _logger.error("Hikvision LP-audit delete errors: %s", "; ".join(errors))
            return {"status": "failed", "error": "; ".join(errors)}
        _logger.debug("Hikvision LP-audit delete OK: %s", [e.get('plateNum') for e in plate_entries])
        return {"status": "success", "response": "deleted %s plate(s)" % len(plate_entries)}

    def _vcl_delete(self, plate_entries):
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
                _logger.debug("Hikvision delete_plate_from_list (VCL): deleted: %s", plate_entries)
                return {"status": "success", "response": response.text}
            error_detail = self._extract_error(response.text)
            _logger.error("Hikvision delete_plate_from_list (VCL): FAILED with status %s. Error: %s",
                          response.status_code, error_detail)
            return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision delete_plate_from_list (VCL): Request error: %s", e, exc_info=True)
            return {"status": "failed", "error": str(e)}

    def search_lp_audit(self, max_results=50, position=0, search_id="0"):
        """Read the plates currently stored on the camera's LP-audit list.

        POSTs the LP-audit search (the only read available on TCG/7-series
        firmware that dropped VCL). One page is returned per call; the caller
        pages by advancing ``position`` until it has read ``total`` records.
        Returns a dict with the raw response body, ``records`` (one dict per
        plate: plate, type, list_category, card_no, effective_time,
        create_time), a convenience ``plates`` list of plate strings, and
        ``total`` (the camera's totalMatches). Used for reconciling the Odoo
        whitelist against what is actually loaded on the device.
        """
        url = (f"http://{self.ip_address}:{self.port}"
               f"/ISAPI/Traffic/channels/{LP_AUDIT_CHANNEL}/searchLPListAudit")
        body = ("<LPListAuditSearchDescription>"
                f"<maxResults>{int(max_results)}</maxResults>"
                f"<searchResultPosition>{int(position)}</searchResultPosition>"
                f"<searchID>{search_id}</searchID>"
                "</LPListAuditSearchDescription>")
        try:
            response = requests.post(url, auth=HTTPDigestAuth(self.username, self.password),
                                     headers={"Content-Type": "application/xml"},
                                     data=body, timeout=self.timeout)
            if response.status_code != 200:
                error_detail = self._extract_error(response.text)
                _logger.error("Hikvision searchLPListAudit FAILED (HTTP %s). Error: %s",
                              response.status_code, error_detail)
                return {"status": "failed", "error": error_detail}
            records, total = self._parse_lp_search(response.text)
            _logger.debug("Hikvision searchLPListAudit OK: %s/%s plate(s) at position %s",
                          len(records), total, position)
            return {"status": "success", "response": response.text, "records": records,
                    "plates": [r["plate"] for r in records], "total": total}
        except Exception as e:
            _logger.error("Hikvision searchLPListAudit: Request error: %s", e, exc_info=True)
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def _parse_lp_search(body):
        """Parse an LP-audit search response into (records, total_matches).

        The camera answers with the ver20 namespace (or none), so element
        lookups match on the local tag name. Each LicensePlateInfo becomes a
        dict; the bucket <type> ('whiteList'/'blackList') is also mapped to the
        Odoo list_category for direct comparison. Returns ([], 0) on an
        unparseable body.
        """
        try:
            root = parse_untrusted_xml(body or "")
        except etree.XMLSyntaxError:
            return [], 0

        def _local(elem, tag):
            return next((c.text for c in elem
                         if c.tag.rsplit("}", 1)[-1] == tag and c.text), None)

        records = []
        total = 0
        for elem in root.iter():
            local = elem.tag.rsplit("}", 1)[-1]
            if local == "totalMatches" and elem.text:
                total = int(elem.text)
            elif local == "LicensePlateInfo":
                plate = _local(elem, "LicensePlate")
                if not plate:
                    continue
                cam_type = _local(elem, "type")
                records.append({
                    "plate": plate,
                    "type": cam_type,
                    "list_category": LP_READ_TYPE_TO_CATEGORY.get(cam_type),
                    "card_no": _local(elem, "cardNo"),
                    "effective_time": _local(elem, "effectiveTime"),
                    "create_time": _local(elem, "createTime"),
                })
        return records, total

    def probe_vcl_capabilities(self):
        """SAFE read-only probe of the legacy VCL capabilities, kept verbatim.

        The self-test wants the camera's literal answer, not our
        interpretation of it: on a live site the routing probe
        (:meth:`_uses_lp_audit_api`) condensed this very answer into one
        boolean and the reason a mechanism was chosen became invisible.
        """
        url = f"http://{self.ip_address}:{self.port}/ISAPI/ITC/Entrance/VCL/capabilities"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password),
                                    timeout=self.timeout)
            return {"status": "success", "status_code": response.status_code,
                    "body": (response.text or "")[:1000]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def export_lp_list_xml(self):
        """SAFE read-only export of the plate list as the camera's own XML.

        GET /ISAPI/Traffic/channels/1/licensePlateAuditData?fileType=xml is the
        documented export half of the list import/export pair, so the document
        it returns is written in EXACTLY the schema this firmware's import
        accepts. When a write is being refused as malformed, this is the
        ground truth to compare against - taken from the device itself, not
        from a manual for some other firmware.
        """
        url = (f"http://{self.ip_address}:{self.port}"
               f"/ISAPI/Traffic/channels/{LP_AUDIT_CHANNEL}/licensePlateAuditData?fileType=xml")
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password),
                                    timeout=self.timeout)
            return {"status": "success", "status_code": response.status_code,
                    "body": (response.text or "")[:1500]}
        except Exception as e:
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
        raise NotImplementedError("get_plate_list is disabled for security reasons.")

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
                root = parse_untrusted_xml(response.content)
                ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}
                timeMode = root.findtext('ns:timeMode', namespaces=ns)
                timeZone = root.findtext('ns:timeZone', namespaces=ns)
                localTime = root.findtext('ns:localTime', namespaces=ns)
                return {"status": "success", "timeMode": timeMode, "timeZone": timeZone, "localTime": localTime}
            else:
                error_detail = self._extract_error(response.text)
                return {"status": "failed", "error": error_detail}
        except Exception as e:
            _logger.error("Hikvision API request failed: %s", e)
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

            root = parse_untrusted_xml(response.content)
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
                root = parse_untrusted_xml(response.content)
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
            _logger.error("Hikvision API request failed: %s", e)
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
            _logger.error("Hikvision API request failed: %s", e)
            return {"status": "failed", "error": str(e)}


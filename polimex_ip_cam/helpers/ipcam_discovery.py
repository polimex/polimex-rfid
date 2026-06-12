import socket
import time
import xml.etree.ElementTree as ET
import requests
from requests.auth import HTTPDigestAuth
import logging

# Use Odoo's log routing — do not attach our own StreamHandler/level here.
logger = logging.getLogger(__name__)


class HikvisionDiscoverer:
    def __init__(self, admin_user="admin", admin_pass="", timeout=1, log_enabled=True):
        """
        Инициализира настройките за автентикация, timeout за мрежови заявки и логването.
        :param admin_user: потребител за достъп до камерите
        :param admin_pass: парола за достъп до камерите
        :param timeout: timeout за мрежови заявки
        :param log_enabled: ако True, се логват съобщения за напредъка
        """
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.timeout = timeout
        self.log_enabled = log_enabled

    def _log(self, message, level=logging.INFO):
        if self.log_enabled:
            logger.log(level, message)

    def _unified_result(self, ip, mac=None, model=None, serial=None, method=None, brand=None):
        """
        Връща унифициран резултат като речник.
        """
        return {
            "ip_address": ip,
            "mac_address": mac,
            "model": model,
            "serial_number": serial,
            "discovery_method": method,
            "brand": brand
        }

    def discover_by_ping(self, network_prefix="192.168.1.", start=1, end=254):
        """
        Открива устройства чрез HTTP заявка към /ISAPI/System/deviceInfo.
        Този метод е насочен към Hikvision устройства.
        """
        results = []
        self._log("Starting discover_by_ping...")
        for i in range(start, end + 1):
            ip = f"{network_prefix}{i}"
            url = f"http://{ip}/ISAPI/System/deviceInfo"
            try:
                resp = requests.get(
                    url,
                    auth=HTTPDigestAuth(self.admin_user, self.admin_pass),
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    self._log(f"IP {ip}: Device responded with status 200.", level=logging.DEBUG)
                    root = ET.fromstring(resp.text)
                    model = root.findtext('.//model')
                    serial = root.findtext('.//serialNumber')
                    results.append(self._unified_result(ip, model=model, serial=serial, method="Ping/HTTP", brand="Hikvision"))
                else:
                    self._log(f"IP {ip}: Received status {resp.status_code}", level=logging.DEBUG)
            except Exception as e:
                self._log(f"IP {ip}: No response or error: {e}", level=logging.DEBUG)
                continue
        self._log("discover_by_ping finished.")
        return results

    def discover_by_ssdp(self, mx=1, st="ssdp:all"):
        """
        Открива устройства чрез SSDP (UPnP).
        Ако отговора съдържа индикация за 'Hikvision', се счита, че устройството е Hikvision.
        """
        results = []
        self._log("Starting discover_by_ssdp...")
        ssdp_request = "\r\n".join([
            "M-SEARCH * HTTP/1.1",
            "HOST: 239.255.255.250:1900",
            "MAN: \"ssdp:discover\"",
            f"MX: {mx}",
            f"ST: {st}",
            "", ""
        ])
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(self.timeout)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        try:
            self._log("Sending SSDP M-SEARCH request...")
            sock.sendto(ssdp_request.encode('utf-8'), ("239.255.255.250", 1900))
            start_time = time.time()
            while time.time() - start_time < mx:
                try:
                    data, addr = sock.recvfrom(1024)
                    ip = addr[0]
                    self._log(f"SSDP response received from {ip}", level=logging.DEBUG)
                    # Ако отговора съдържа "Hikvision"
                    if b"Hikvision" in data:
                        self._log(f"IP {ip}: Identified as Hikvision device via SSDP.", level=logging.DEBUG)
                        url = f"http://{ip}/ISAPI/System/deviceInfo"
                        try:
                            resp = requests.get(
                                url,
                                auth=HTTPDigestAuth(self.admin_user, self.admin_pass),
                                timeout=self.timeout
                            )
                            if resp.status_code == 200:
                                root = ET.fromstring(resp.text)
                                model = root.findtext('.//model')
                                serial = root.findtext('.//serialNumber')
                                results.append(self._unified_result(ip, model=model, serial=serial, method="SSDP", brand="Hikvision"))
                        except Exception as e:
                            self._log(f"IP {ip}: Error during HTTP GET for deviceInfo: {e}", level=logging.DEBUG)
                            results.append(self._unified_result(ip, method="SSDP", brand="Hikvision"))
                except socket.timeout:
                    break
        finally:
            sock.close()
        self._log("discover_by_ssdp finished.")
        return results

    def discover_by_sadp(self, broadcast_address="255.255.255.255", port=37020):
        """
        Открива устройства чрез SADP – използва UDP broadcast и очаква отговори.
        Подразбира се, че тези отговори са от Hikvision устройства.
        """
        results = []
        self._log("Starting discover_by_sadp...")
        sadp_probe = b"<SADP><Cmd>Probe</Cmd></SADP>"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(self.timeout)
        try:
            self._log(f"Sending SADP probe to {broadcast_address}:{port} ...")
            sock.sendto(sadp_probe, (broadcast_address, port))
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    ip = addr[0]
                    self._log(f"SADP response received from {ip}", level=logging.DEBUG)
                    try:
                        root = ET.fromstring(data.decode('utf-8'))
                        model = root.findtext('.//model')
                        serial = root.findtext('.//serialNumber')
                        results.append(self._unified_result(ip, model=model, serial=serial, method="SADP", brand="Hikvision"))
                    except Exception as e:
                        self._log(f"IP {ip}: Error parsing SADP response: {e}", level=logging.DEBUG)
                        results.append(self._unified_result(ip, method="SADP", brand="Hikvision"))
                except socket.timeout:
                    break
        finally:
            sock.close()
        self._log("discover_by_sadp finished.")
        return results

    def discover_by_dahua(self, network_prefix="192.168.1.", start=1, end=254):
        """
        Открива Dahua устройства чрез опит за достъп до специфичния Dahua endpoint.
        Използва URL: /cgi-bin/magicBox?cmd=getDevInfo, който обикновено връща информация за Dahua устройства.
        """
        results = []
        self._log("Starting discover_by_dahua...")
        for i in range(start, end + 1):
            ip = f"{network_prefix}{i}"
            url = f"http://{ip}/cgi-bin/magicBox?cmd=getDevInfo"
            try:
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    self._log(f"IP {ip}: Dahua device responded.", level=logging.DEBUG)
                    try:
                        # Опит за парсване на XML
                        root = ET.fromstring(resp.text)
                        model = root.findtext('.//deviceName')
                        serial = root.findtext('.//SerialNumber')
                    except ET.ParseError:
                        # Ако не е XML, опит за JSON
                        data = resp.json()
                        model = data.get("deviceName")
                        serial = data.get("SerialNumber")
                    results.append(self._unified_result(ip, model=model, serial=serial, method="Dahua Ping", brand="Dahua"))
            except Exception as e:
                self._log(f"IP {ip}: Dahua discovery error: {e}", level=logging.DEBUG)
                continue
        self._log("discover_by_dahua finished.")
        return results

    def discover_all(self):
        """
        Изпълнява всички методи за откриване и връща обединен списък от уникални устройства.
        Уникалността се базира върху сериен номер или IP адрес.
        """
        self._log("Starting discover_all...")
        devices = {}
        methods = [self.discover_by_ping, self.discover_by_ssdp, self.discover_by_sadp, self.discover_by_dahua]
        for method in methods:
            try:
                result_list = method()
                for device in result_list:
                    key = device.get("serial_number") or device.get("ip_address")
                    if key in devices:
                        if device.get("discovery_method") not in devices[key]["discovery_method"]:
                            devices[key]["discovery_method"] += f", {device.get('discovery_method')}"
                    else:
                        devices[key] = device
            except Exception as e:
                self._log(f"Error in method {method.__name__}: {e}", level=logging.ERROR)
        self._log("discover_all finished.")
        return list(devices.values())

# Примерна употреба
if __name__ == "__main__":
    # За да видите логовете, оставете log_enabled=True
    discoverer = HikvisionDiscoverer(admin_user="admin", admin_pass="", timeout=1, log_enabled=True)
    devices = discoverer.discover_all()
    for device in devices:
        print(device)

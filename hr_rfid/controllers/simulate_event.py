#!/usr/bin/env python3
"""
Simulate RFID event to local Odoo endpoint.
Author: Polimex Dev Team
"""

import requests

def simulate_event():
    url = "http://localhost:8018/hr/rfid/event"
    payload = {
        "convertor": 414468,
        "event": {
            "bos": 1,
            "card": "1786802811",
            "cmd": "FA",
            "date": "05.06.25",
            "day": 2,
            "dt": "000000000000000000000004",
            "err": 0,
            "event_n": 3,
            "id": 40,
            "reader": 1,
            "time": "15:40:55",
            "tos": 1
        },
        "key": "7411"
    }
    headers = {"Content-Type": "application/json"}

    resp = requests.post(url, json=payload, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response body: {resp.text}")

if __name__ == "__main__":
    simulate_event()

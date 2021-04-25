{'convertor': 411388, 'event': {'bos': 1, 'card': '0016548033', 'cmd': 'FA', 'date': '03.10.21', 'day': 3, 'dt': '0000', 'err': 0, 'event_n': 64, 'id': 27, 'reader': 1, 'time': '11:59:23', 'tos': 1}, 'key': '4CEC'}
curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "webstack.notification", "params": {"convertor": 411388, "event": {"bos": 1, "card": "0016548033", "cmd": "FA", "date": "03.10.21", "day": 3, "dt": "0000", "err": 0, "event_n": 64, "id": 27, "reader": 1, "time": "12:14", "tos": 1}, "key": "4CEC"}}' \
    http://localhost:8014/hr/rfid/event

{'jsonrpc': '2.0', 'method': 'webstack.notification', 'params': {'FW': '1.54', 'convertor': 411388, 'heartbeat': 54, 'key': '4CEC'}}
{"jsonrpc": "2.0", "method": "webstack.notification", "params": {"convertor": 411388, "event": {"bos": 1, "card": "0016548033", "cmd": "FA", "date": "03.10.21", "day": 3, "dt": "0000", "err": 0, "event_n": 64, "id": 27, "reader": 1, "time": "12:14", "tos": 1}, "key": "4CEC"}}
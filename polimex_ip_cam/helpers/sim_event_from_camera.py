#!/usr/bin/env python3
import json
import base64
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import argparse

def simulate_request(log_file_path, controller_url):
    try:
        with open(log_file_path, "r") as log_file:
            lines = log_file.readlines()
    except Exception as e:
        print(f"Error reading log file {log_file_path}: {e}")
        return

    if not lines:
        print("No logged requests found.")
        return

    last_log = lines[-1]
    try:
        log_data = json.loads(last_log)
    except Exception as e:
        print(f"Error parsing log file JSON: {e}")
        return

    form_data = log_data.get("form", {})
    files_data = log_data.get("files", {})

    multipart_fields = {}
    for key, value in form_data.items():
        multipart_fields[key] = str(value)

    for filename, b64_data in files_data.items():
        file_content = base64.b64decode(b64_data)
        if filename.lower().endswith('.jpg'):
            mimetype = 'image/jpeg'
        elif filename.lower().endswith('.xml'):
            mimetype = 'text/xml'
        else:
            mimetype = 'application/octet-stream'
        multipart_fields[filename] = (filename, file_content, mimetype)

    encoder = MultipartEncoder(fields=multipart_fields)
    headers = log_data.get("headers", {})
    headers["Content-Type"] = encoder.content_type
    headers.pop("Content-Length", None)
    headers.pop("Host", None)

    print("Simulating request to:", controller_url)
    print("Multipart fields:", multipart_fields.keys())
    try:
        response = requests.post(controller_url, headers=headers, data=encoder)
        print("Response status code:", response.status_code)
        print("Response text:", response.text)
    except Exception as e:
        print("Error during POST request:", e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Simulate IP camera event request using logged request data.'
    )
    parser.add_argument(
        '-l', '--log-file', type=str, default='request1',
        help='Path to the log file containing the raw request data'
    )
    parser.add_argument(
        '-u', '--url', type=str, default='http://localhost:8018/ipcam/anpr/event',
        help='Controller endpoint URL'
    )
    args = parser.parse_args()
    simulate_request(args.log_file, args.url)

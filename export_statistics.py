"""
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""
from dnacentersdk import api
from dotenv import load_dotenv
import influxdb_client as db
from influxdb_client.client.write_api import SYNCHRONOUS
from dnacentersdk.exceptions import ApiError
import os, sys
from time import sleep
import requests
import json
import time
from urllib3.exceptions import ConnectTimeoutError

# Load environment variables
load_dotenv()

# Fetch DNAC config
DNAC_HOST = os.getenv("DNAC_HOST")
DNAC_USER = os.getenv("DNAC_USER")
DNAC_PASSWORD = os.getenv("DNAC_PASSWORD")
TRACKED_CLIENTS = os.getenv("TRACKED_CLIENTS")
COLLECTION_INTERVAL = os.getenv("COLLECTION_INTERVAL")

# Fetch InfluxDB config
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")

# Establish connection to DNAC
try:
    print(f"Attempting connection to {DNAC_HOST} as user {DNAC_USER}")
    dnac = api.DNACenterAPI(
        username=DNAC_USER,
        password=DNAC_PASSWORD,
        base_url=f"https://{DNAC_HOST}",
        verify=False,
    )
except Exception as e:
    print("Failed to connect to DNA Center")
    print(f"Error: {e}")
    sys.exit(1)


def getIssues():
    """
    Return all active DNAC issues
    """
    issues = dnac.issues.issues(issue_status="ACTIVE")
    issue_list = {}
    name = "DNAC Server"
    issue_list[name] = {}
    issue_list[name]["measurement"] = "issues"
    issue_list[name]["location"] = "Global"
    issue_list[name]["fields"] = {}
    issue_list[name]["fields"]["issue_count"] = int(len(issues.response))
    print(f"Found {len(issues)} active issues")
    return issue_list


def getAllClients():
    """
    Query all DNAC wireless clients
    """
    # Unofficial / Unsupported API call to query all hosts
    url = dnac._session.base_url + "/api/assurance/v1/host"
    # Query client details for last 60 seconds
    end = (int(time.time()) * 1000) - 10000
    start = end - 60000
    search_filter = {
        "starttime": start,
        "endtime": end,
        "filters": {"devType": ["WIRELESS"]},
    }
    headers = {"X-auth-token": dnac.access_token, "content-type": "application/json"}
    response = requests.post(
        url, data=json.dumps(search_filter), headers=headers, verify=False
    )
    wireless_macs = [client["id"] for client in response.json()["response"]]
    print(f"Found {len(wireless_macs)} wireless clients")
    return wireless_macs


def getClientDetails(client_macs):
    """
    Query Client Health details from DNAC
    """
    clientlist = {}
    for mac in client_macs:
        print(f"Getting details for client at {mac}")
        details = dnac.clients.get_client_detail(mac_address=mac)
        if len(details.detail) == 0:
            print(f"No details for client at {mac}")
            continue
        clientlist[mac] = details.detail
    return clientlist


def parseClientDetails(api_data):
    """
    Generate Influx payload from client detail
    """
    client_data = {}
    for client in api_data:
        info = api_data[client]
        # Not all devices will display a hostname
        if info["hostName"]:
            name = info["hostName"]
        else:
            name = client
        print("Parsing measurements for client: " + name)

        # Generate base Influx payload structure
        client_data[name] = {}
        client_data[name]["measurement"] = "client"
        client_data[name]["location"] = info["location"]
        client_data[name]["fields"] = {}

        # Add Health Score measurements
        for score in info["healthScore"]:
            if score["healthType"] == "OVERALL":
                client_data[name]["fields"]["overall_health"] = score["score"]
            if score["healthType"] == "ONBOARDED":
                client_data[name]["fields"]["onboard_health"] = score["score"]
            if score["healthType"] == "CONNECTED":
                client_data[name]["fields"]["connect_health"] = score["score"]
        # Add Wireless stats
        if info["ssid"]:
            client_data[name]["fields"]["connected_ssid"] = info["ssid"]
        if info["clientConnection"]:
            client_data[name]["fields"]["connected_ap"] = info["clientConnection"]
        if info["frequency"]:
            client_data[name]["fields"]["frequency"] = float(info["frequency"])
        if info["channel"]:
            client_data[name]["fields"]["channel"] = float(info["channel"])
        if info["rssi"]:
            client_data[name]["fields"]["rssi"] = float(info["rssi"])
        if info["avgRssi"]:
            client_data[name]["fields"]["avgRssi"] = float(info["avgRssi"])
        if info["snr"]:
            client_data[name]["fields"]["snr"] = float(info["snr"])
        if info["avgSnr"]:
            client_data[name]["fields"]["avgSnr"] = float(info["avgSnr"])
        if info["dnsResponse"]:
            client_data[name]["fields"]["dnsResponse"] = float(info["dnsResponse"])
        if info["dnsRequest"]:
            client_data[name]["fields"]["dnsRequest"] = float(info["dnsRequest"])
        if info["dataRate"]:
            client_data[name]["fields"]["dataRate"] = float(info["dataRate"])
    return client_data


def getDeviceDetails(devicetype):
    """
    Query Device details from DNAC
    """
    devices = dnac.devices.get_device_list(family=devicetype)
    devicelist = {}
    print(f"Found {len(devices.response)} devices of type {devicetype}")
    for device in devices.response:
        print(f"Getting details for device: " + device["hostname"])
        try:
            details = dnac.devices.get_device_detail(
                identifier="uuid", search_by=device["id"]
            )
            if len(details.response) == 0:
                print("No details for device: " + device)
                continue
            devicelist[device["id"]] = details.response
        except ApiError as e:
            print(f"Could not query details for device: {device['hostname']}")
            print(f"Error: {e}")
    return devicelist


def parseDeviceDetails(device_type, api_data):
    """
    Generate Influx payload from device detailed info
    """
    device_data = {}
    for device in api_data:
        info = api_data[device]
        name = info["nwDeviceName"]
        print("Parsing measurements for device: " + name)
        # Generate base Influx payload structure
        device_data[name] = {}
        device_data[name]["measurement"] = device_type
        device_data[name]["location"] = info["location"]
        device_data[name]["fields"] = {}

        # AP-specific: Connectivity Status & Uptime
        if device_type == "ap":
            device_data[name]["fields"]["connectivityStatus"] = info[
                "connectivityStatus"
            ]
            device_data[name]["fields"]["upTime"] = int(info["upTime"])
        # Communication State
        device_data[name]["fields"]["communicationState"] = info["communicationState"]
        # Overall Health
        device_data[name]["fields"]["overallHealth"] = info["overallHealth"]
        # Memory Score
        device_data[name]["fields"]["memoryScore"] = info["memoryScore"]
        # CPU Score
        device_data[name]["fields"]["cpuScore"] = info["cpuScore"]
    return device_data


def writeInfluxDB(data):
    """
    Write payload to InfluxDB
    """
    print("Writing to influx...")
    client = db.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
    except ConnectTimeoutError as e:
        print("Failed to connect to influx" + e)
        return
    measurements = []
    for item in data:
        m = data[item]
        for f in m["fields"]:
            p = (
                db.Point(m["measurement"])
                .tag("location", m["location"])
                .tag("hostname", item)
                .field(f, m["fields"][f])
            )
            measurements.append(p)
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=measurements)
        client.close()
    except db.rest.ApiException as e:
        print("Error writing to influx: " + e)
        client.close()


if __name__ == "__main__":
    try:
        while True:
            print("Collecting Wireless Controller details...")
            wlc_details = getDeviceDetails("Wireless Controller")
            data = parseDeviceDetails("wlc", wlc_details)
            writeInfluxDB(data)

            print("\nCollecting Access Point details...")
            ap_details = getDeviceDetails("Unified AP")
            data = parseDeviceDetails("ap", ap_details)
            writeInfluxDB(data)

            print("\nCollecting Wireless Client details...")
            if TRACKED_CLIENTS:
                print("Using TRACKED_CLIENTS list")
                client_macs = TRACKED_CLIENTS.split(",")
                client_details = getClientDetails(client_macs)
            else:
                print("Querying all clients from DNAC...")
                client_macs = getAllClients()
                client_details = getClientDetails(client_macs)
            data = parseClientDetails(client_details)
            writeInfluxDB(data)

            print("\nChecking for DNAC active issues...")
            active_issues = getIssues()
            writeInfluxDB(active_issues)

            print(f"\nDone. Next run in {COLLECTION_INTERVAL} seconds...\n\n")
            sleep(int(COLLECTION_INTERVAL))
    except KeyboardInterrupt:
        print("Quitting...")

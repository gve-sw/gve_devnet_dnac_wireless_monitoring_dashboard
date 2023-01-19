# DNA Center - Wireless Client Monitoring Dashboard

This repo contains example code for a DNA Center wireless client monitoring dashboard.

This code will:

- Connect to DNA Center
- Export metrics & health scores for Wireless Controllers and Access Points
- Export metrics for all wireless clients, or optionally a specific list of wireless clients
- Metrics are imported into InfluxDB
- Grafana can be used to build a dynamic dashboard based on these metrics

## Contacts

- Matt Schmitz (mattsc@cisco.com)

## Solution Components

- Cisco DNA Center
- Cisco Catalyst 9800 Wireless Controller
- Cisco Catalyst 9100 Series Access Points
- Grafana
- InfluxDB

## Installation/Configuration

*Note:* This code requires a new or existing [InfluxDB](https://docs.influxdata.com/influxdb/v2.6/install/) & [Grafana](https://grafana.com/docs/grafana/latest/setup-grafana/installation/) installation to use.

### **1 - Clone repo**

```bash
git clone <repo_url>
```

### **2 - Install dependancies**

```bash
pip install -r requirements.txt
```

### **3 - Set Environment Variables**

In order to use this code, a few configuration items must be provided via environment variables.

A sample `.env` file has been provided which can be used. This file contains the following environment variables, which must be configured:

```bash
#
# InfluxDB configuration
#

# Influx DB URL, in format http://<host>:<port>
INFLUX_URL=
# Influx DB access token
INFLUX_TOKEN=
# Target bucket
INFLUX_BUCKET=
# Target organization
INFLUX_ORG=

#
# DNA Center configuration
#

# IP or host name of DNA Center
DNAC_HOST=
# DNAC credentials for API Access
DNAC_USER=
DNAC_PASSWORD=
# Optional list of MAC addresses, separated by comma. If not set, all wireless clients are queried
TRACKED_CLIENTS=
# Interval to collect statistics from DNA Center, in seconds
COLLECTION_INTERVAL=
```

**Note**: For `TRACKED_CLIENTS` - if this field is left empty, all wireless clients will be queried in DNA Center. However, this can be limited to only a certain set of clients by defining them here (MAC addresses, comma separated). For example, if we had two MAC addresses to track, then we would set the following: `TRACKED_CLIENTS=AA:AA:AA:AA:AA:AA,BB:BB:BB:BB:BB:BB`

### **4 - Run script**

Run the script with the following command:

```bash
python3 export_statistics.py
```

Script will run on a loop, querying DNA Center based on the interval defined by `COLLECTION_INTERVAL`.

### **5 - Import Grafana Dashboards**

Within the `grafana` folder, there are two JSON files for each dashboard.

There is a primary wireless health overview dashboard. Within this dashboard, the client health widgets can be clicked on to drill into client-specific details. Thie client details page is another dashboard.

Import both of these dashboard into Grafana by going to the **Dashboards** page, and clicking **Import Dashboard**.

# Screenshots

### **Example of main monitoring dashboard:**

![/IMAGES/example-dashboard.PNG](/IMAGES/example-dashboard.PNG)

### **Example of client drilldown:**

![/IMAGES/example-client-drilldown.PNG](/IMAGES/example-client-drilldown.PNG)

### LICENSE

Provided under Cisco Sample Code License, for details see [LICENSE](LICENSE.md)

### CODE_OF_CONDUCT

Our code of conduct is available [here](CODE_OF_CONDUCT.md)

### CONTRIBUTING

See our contributing guidelines [here](CONTRIBUTING.md)

#### DISCLAIMER

<b>Please note:</b> This script is meant for demo purposes only. All tools/ scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.
You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.

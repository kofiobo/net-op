import paramiko
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import urllib3

# Suppress SSL warnings for Unifi controllers
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Controller Information
controllers = [
    {"type": "Ericsson", "ip": "10.209.98.60", "username": "root", "password": "admin123"},
    {"type": "Cisco", "ip": "192.168.1.122", "username": "Admin", "password": "Password@123"},
    {"type": "Cisco", "ip": "192.168.0.222", "username": "Admin", "password": "Password@123"},
    {"type": "Unifi", "ip": "192.168.1.83", "username": "admin", "password": "unifi@knust"},
    {"type": "Unifi", "ip": "192.168.0.183", "username": "admin", "password": "unifi@knust"}
]

# Placeholder for results
data = []

def fetch_ap_status(controller):
    """Fetches active and inactive APs from each controller and appends to data list."""
    try:
        if controller["type"] == "Ericsson":
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(controller["ip"], username=controller["username"], password=controller["password"])
            stdin, stdout, stderr = client.exec_command("show ap status")  # Verify correct command
            ap_data = stdout.read().decode()
            client.close()

            for line in ap_data.splitlines():
                if "AP" in line:
                    ap_name, status = line.split()[:2]
                    data.append({"Controller Type": "Ericsson", "Controller IP": controller["ip"], 
                                 "AP Name": ap_name, "Status": status})

        elif controller["type"] == "Cisco":
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(controller["ip"], username=controller["username"], password=controller["password"])
            stdin, stdout, stderr = client.exec_command("show ap summary")  # Verify correct command
            ap_data = stdout.read().decode()
            client.close()

            for line in ap_data.splitlines():
                if "AP" in line:
                    ap_name, status = line.split()[:2]
                    data.append({"Controller Type": "Cisco", "Controller IP": controller["ip"], 
                                 "AP Name": ap_name, "Status": status})

        elif controller["type"] == "Unifi":
            url = f"https://{controller['ip']}:8443/api/s/default/stat/device"
            response = requests.get(url, auth=(controller["username"], controller["password"]), verify=False)
            response.raise_for_status()
            ap_data = response.json()["data"]

            for ap in ap_data:
                ap_name = ap.get("name", "Unknown")
                status = "Active" if ap.get("state") == 1 else "Inactive"
                data.append({"Controller Type": "Unifi", "Controller IP": controller["ip"], 
                             "AP Name": ap_name, "Status": status})
    
    except Exception as e:
        print(f"Error fetching data from {controller['ip']}: {e}")

# Run extraction in parallel
with ThreadPoolExecutor() as executor:
    executor.map(fetch_ap_status, controllers)

# Create DataFrame
df = pd.DataFrame(data)

# Check if data collection was successful
if not df.empty and "Status" in df.columns:
    active_count = df[df["Status"] == "Active"].shape[0]
    inactive_count = df[df["Status"] == "Inactive"].shape[0]

    # Print totals
    print(f"Total Active APs: {active_count}")
    print(f"Total Inactive APs: {inactive_count}")

    # Save data to Excel
    df.to_excel("AP_Status_Report.xlsx", index=False)
    print("AP Status Report generated successfully.")
else:
    print("No data was collected. Please check connection and command configurations.")

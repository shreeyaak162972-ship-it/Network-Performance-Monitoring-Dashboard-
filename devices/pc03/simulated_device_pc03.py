"""
simulated_device_pc03.py  --  PC-03
-----------------------------------
Simulated monitoring device that generates periodic network-performance
metrics, prints them to the terminal, and POSTs them to the Flask
dashboard API at /api/metrics.

Run with:
    docker compose up monitor-pc-03

CONFIGURATION
-------------
Edit the values in the CONFIG block below to change what PC-03 reports.
"""

import time
import datetime
import random
import requests   # used to POST metrics to the Flask API


# ---------------------------------------------------------------------------
# DEVICE IDENTITY
# ---------------------------------------------------------------------------
DEVICE_NAME = "PC-03"
DEVICE_TYPE = "Simulated PC"

# ---------------------------------------------------------------------------
# FLASK API URL
# Uses the Docker service name 'web' so this works inside the Docker network.
# Change to http://localhost:5000/api/metrics if running outside Docker.
# ---------------------------------------------------------------------------
FLASK_API_URL = "http://web:5000/api/metrics"


# ---------------------------------------------------------------------------
# SIMULATED METRIC VALUES
# Baseline configuration for PC-03.
# ---------------------------------------------------------------------------

CPU_USAGE         = 72      # percent  (0 – 100)
CPU_VARIATION     = 8       # ± random jitter around CPU_USAGE

MEMORY_USAGE      = 68      # percent  (0 – 100)
MEMORY_VARIATION   = 5       # ± random jitter around MEMORY_USAGE

NET_SENT_MB       = 3.5     # megabytes sent per interval
NET_RECV_MB       = 8.0     # megabytes received per interval

LATENCY_MS        = 22      # milliseconds
LATENCY_VARIATION = 4       # ± random jitter around LATENCY_MS

PACKET_LOSS       = 2       # percent

DEVICE_STATUS     = "Online"   # "Online" or "Offline"

# How often (in seconds) to emit a new reading.
REPORT_INTERVAL_SECONDS = 5


# ---------------------------------------------------------------------------
# METRIC COLLECTION FUNCTIONS
# Each function returns the metric value for one reading with small jitter.
# ---------------------------------------------------------------------------

def get_cpu_usage():
    """Return CPU usage with random variation."""
    value = CPU_USAGE + random.uniform(-CPU_VARIATION, CPU_VARIATION)
    return round(max(0.0, min(100.0, value)), 1)


def get_memory_usage():
    """Return memory usage with random variation."""
    value = MEMORY_USAGE + random.uniform(-MEMORY_VARIATION, MEMORY_VARIATION)
    return round(max(0.0, min(100.0, value)), 1)


def get_network_sent_mb():
    """Return simulated megabytes sent (with tiny jitter)."""
    return round(NET_SENT_MB + random.uniform(-0.1, 0.1), 2)


def get_network_recv_mb():
    """Return simulated megabytes received (with tiny jitter)."""
    return round(NET_RECV_MB + random.uniform(-0.2, 0.2), 2)


def get_latency_ms():
    """Return network latency in milliseconds (with jitter)."""
    value = LATENCY_MS + random.uniform(-LATENCY_VARIATION, LATENCY_VARIATION)
    return round(max(0.0, value), 1)


def get_packet_loss():
    """Return packet loss percentage."""
    return float(PACKET_LOSS)


def get_device_status():
    """Return the device status string."""
    return DEVICE_STATUS


# ---------------------------------------------------------------------------
# REPORTING
# Collects all metrics and prints them in a readable block.
# ---------------------------------------------------------------------------

def collect_metrics():
    """Gather all metric values and return them as a dictionary."""
    return {
        "device_name":   DEVICE_NAME,
        "device_type":   DEVICE_TYPE,
        "timestamp":     datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status":        get_device_status(),
        "cpu_usage":     get_cpu_usage(),
        "memory_usage":  get_memory_usage(),
        "net_sent_mb":   get_network_sent_mb(),
        "net_recv_mb":   get_network_recv_mb(),
        "latency_ms":    get_latency_ms(),
        "packet_loss":   get_packet_loss(),
    }


def print_metrics(metrics):
    """Print the collected metrics in a clean, readable format."""
    print("=" * 48)
    print(f"  Device : {metrics['device_name']}  ({metrics['device_type']})")
    print(f"  Time   : {metrics['timestamp']}")
    print(f"  Status : {metrics['status']}")
    print("-" * 48)
    print(f"  CPU Usage      : {metrics['cpu_usage']} %")
    print(f"  Memory Usage   : {metrics['memory_usage']} %")
    print(f"  Net Sent       : {metrics['net_sent_mb']} MB")
    print(f"  Net Received   : {metrics['net_recv_mb']} MB")
    print(f"  Latency        : {metrics['latency_ms']} ms")
    print(f"  Packet Loss    : {metrics['packet_loss']} %")
    print("=" * 48)


# ---------------------------------------------------------------------------
# SENDING
# POSTs the collected metrics as JSON to the Flask API endpoint.
# If Flask is not reachable yet, prints a clear warning and continues.
# ---------------------------------------------------------------------------

def send_metrics(metrics):
    """Send the metrics dict to the Flask /api/metrics endpoint."""
    try:
        response = requests.post(
            FLASK_API_URL,
            json=metrics,
            timeout=5   # give Flask 5 seconds to respond
        )
        if response.status_code == 201:
            print(f"  [Sent]  -> Flask accepted the data (HTTP 201)")
        else:
            print(f"  [Warn]  -> Flask returned HTTP {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        print(f"  [Warn]  -> Could not reach Flask at {FLASK_API_URL}. Will retry next interval.")
    except requests.exceptions.Timeout:
        print(f"  [Warn]  -> Request to Flask timed out. Will retry next interval.")
    except Exception as e:
        print(f"  [Warn]  -> Unexpected error sending metrics: {e}")


# ---------------------------------------------------------------------------
# MAIN LOOP
# Runs forever, emitting one reading every REPORT_INTERVAL_SECONDS.
# ---------------------------------------------------------------------------

def run():
    """Start the monitoring loop for PC-03."""
    print(f"[{DEVICE_NAME}] Starting simulated monitoring agent ...")
    print(f"[{DEVICE_NAME}] Reporting every {REPORT_INTERVAL_SECONDS} second(s). Press Ctrl+C to stop.\n")

    while True:
        metrics = collect_metrics()
        print_metrics(metrics)    # always print to terminal
        send_metrics(metrics)     # POST to Flask (safe, will not crash on error)
        time.sleep(REPORT_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()

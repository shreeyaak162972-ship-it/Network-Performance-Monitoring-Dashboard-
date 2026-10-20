"""
monitor_agent.py
----------------
A standalone monitoring agent that collects basic system and network
performance metrics from the device it runs on.

Run directly:
    python monitor_agent.py

No Flask routes, no database connections, no data sending — just
collection and terminal output for now.
"""

import socket
import subprocess
import platform
import re

import psutil  # Third-party library for system/process metrics


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The host used to measure network latency and packet loss.
# Change this to any reachable IP address or hostname you prefer.
PING_TARGET = "8.8.8.8"

# How many ICMP packets to send during the ping test.
PING_COUNT = 4


# ---------------------------------------------------------------------------
# 1. CPU metrics
# ---------------------------------------------------------------------------

def get_cpu_usage():
    """
    Return the current CPU usage as a percentage (0.0 - 100.0).

    interval=1 means psutil samples the CPU for 1 second, which gives
    a more accurate reading than an instant snapshot.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        return cpu_percent
    except Exception as e:
        print(f"  [Warning] Could not read CPU usage: {e}")
        return None


# ---------------------------------------------------------------------------
# 2. Memory / RAM metrics
# ---------------------------------------------------------------------------

def get_memory_usage():
    """
    Return the current RAM usage as a percentage (0.0 - 100.0).

    psutil.virtual_memory() also exposes .total, .available, etc.
    if you need raw byte values later.
    """
    try:
        mem = psutil.virtual_memory()
        return mem.percent
    except Exception as e:
        print(f"  [Warning] Could not read memory usage: {e}")
        return None


# ---------------------------------------------------------------------------
# 3. Network I/O counters
# ---------------------------------------------------------------------------

def get_network_io():
    """
    Return a dict with cumulative bytes sent and received since boot.

    {'bytes_sent': int, 'bytes_recv': int}

    These are totals across ALL network interfaces on the device.
    """
    try:
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
        }
    except Exception as e:
        print(f"  [Warning] Could not read network I/O: {e}")
        return {"bytes_sent": None, "bytes_recv": None}


# ---------------------------------------------------------------------------
# 4. Device identity - hostname and IP address
# ---------------------------------------------------------------------------

def get_device_info():
    """
    Return a dict with the device hostname and its local IP address.

    {'hostname': str, 'ip_address': str or 'Unavailable'}

    socket.gethostbyname() may fail on some networks (e.g. no DNS),
    so we fall back to 'Unavailable' instead of crashing.
    """
    hostname = socket.gethostname()

    try:
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror:
        # DNS resolution failed - the hostname cannot be resolved to an IP.
        ip_address = "Unavailable"

    return {
        "hostname": hostname,
        "ip_address": ip_address,
    }


# ---------------------------------------------------------------------------
# 5. Network connectivity - latency and packet loss via ping
# ---------------------------------------------------------------------------

def ping_target(target=PING_TARGET, count=PING_COUNT):
    """
    Ping *target* and return latency (ms) and packet loss (%).

    Returns a dict:
        {
            'target':       str,   # The hostname/IP that was pinged
            'latency_ms':   float, # Average round-trip time in milliseconds
            'packet_loss':  float, # Packet loss as a percentage (0-100)
            'reachable':    bool,  # True if at least one reply was received
        }

    Works on Windows, Linux, and macOS by adapting the ping command flags.
    If ping is not available or fails completely, all numeric values are None.
    """
    result = {
        "target": target,
        "latency_ms": None,
        "packet_loss": None,
        "reachable": False,
    }

    # Build the correct ping command for the current operating system.
    os_name = platform.system().lower()
    if os_name == "windows":
        # -n count   : number of packets
        cmd = ["ping", "-n", str(count), target]
    else:
        # -c count   : number of packets  (-W 2 = 2-second timeout per packet)
        cmd = ["ping", "-c", str(count), "-W", "2", target]

    try:
        # Run ping and capture its stdout; timeout guards against hangs.
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=count * 5,   # generous timeout: 5 s per packet
        )
        output = proc.stdout + proc.stderr

        # --- Parse packet loss -------------------------------------------
        # Both Windows and Unix include a "% loss" or "% packet loss" figure.
        loss_match = re.search(r"(\d+)%\s*(packet\s*)?loss", output, re.IGNORECASE)
        if loss_match:
            result["packet_loss"] = float(loss_match.group(1))

        # --- Parse average latency ---------------------------------------
        # Linux/macOS:  "rtt min/avg/max/mdev = 10.1/12.3/14.5/1.1 ms"
        # Windows:      "Average = 12ms"
        avg_match = re.search(
            r"(?:Average\s*=\s*(\d+)\s*ms|"
            r"(?:min/avg/max[^=]*=\s*[\d.]+/([\d.]+)))",
            output,
            re.IGNORECASE,
        )
        if avg_match:
            raw = avg_match.group(1) or avg_match.group(2)
            if raw:
                result["latency_ms"] = float(raw)

        # Device is reachable if packet loss is less than 100 %.
        if result["packet_loss"] is not None and result["packet_loss"] < 100:
            result["reachable"] = True
        elif result["latency_ms"] is not None:
            result["reachable"] = True

    except FileNotFoundError:
        # ping binary not found on this system.
        print(f"  [Warning] 'ping' command not found. Cannot test connectivity to {target}.")
    except subprocess.TimeoutExpired:
        print(f"  [Warning] Ping to {target} timed out after {count * 5} seconds.")
    except Exception as e:
        print(f"  [Warning] Unexpected error during ping: {e}")

    return result


# ---------------------------------------------------------------------------
# Helper - format byte counts into human-readable strings
# ---------------------------------------------------------------------------

def _format_bytes(num_bytes):
    """Convert a raw byte count into a human-readable string (KB / MB / GB)."""
    if num_bytes is None:
        return "N/A"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


# ---------------------------------------------------------------------------
# Main - collect everything and print to the terminal
# ---------------------------------------------------------------------------

def collect_and_print():
    """
    Gather all metrics and display them in a readable format.
    This is the main entry point when the script is run directly.
    """
    print("=" * 50)
    print("   Network Performance Monitoring Agent")
    print("=" * 50)

    # -- Device identity ---------------------------------------------------
    print("\n[Device Information]")
    device = get_device_info()
    print(f"  Hostname   : {device['hostname']}")
    print(f"  IP Address : {device['ip_address']}")

    # -- CPU ---------------------------------------------------------------
    print("\n[CPU]")
    cpu = get_cpu_usage()
    print(f"  Usage      : {cpu:.1f}%" if cpu is not None else "  Usage      : N/A")

    # -- Memory ------------------------------------------------------------
    print("\n[Memory / RAM]")
    mem = get_memory_usage()
    print(f"  Usage      : {mem:.1f}%" if mem is not None else "  Usage      : N/A")

    # -- Network I/O -------------------------------------------------------
    print("\n[Network I/O  (cumulative since boot)]")
    net = get_network_io()
    print(f"  Bytes Sent : {_format_bytes(net['bytes_sent'])}")
    print(f"  Bytes Recv : {_format_bytes(net['bytes_recv'])}")

    # -- Connectivity ------------------------------------------------------
    print(f"\n[Connectivity  ->  {PING_TARGET}]")
    ping = ping_target()
    reachable_str = "Yes" if ping["reachable"] else "No"
    latency_str   = f"{ping['latency_ms']:.1f} ms" if ping["latency_ms"] is not None else "N/A"
    loss_str      = f"{ping['packet_loss']:.0f}%"  if ping["packet_loss"]  is not None else "N/A"

    print(f"  Reachable  : {reachable_str}")
    print(f"  Latency    : {latency_str}")
    print(f"  Packet Loss: {loss_str}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    collect_and_print()

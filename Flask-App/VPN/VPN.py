from flask import Flask, jsonify
import subprocess
import os
from dotenv import load_dotenv
import signal

load_dotenv()

def vpn_on():
    """Starts the OpenVPN process."""
    if os.path.exists(os.getenv("PID_FILE")):
        return jsonify({"status": "VPN is already running."}), 409

    try:
        command = [
            'sudo', 'openvpn', '--config', os.getenv("VPN_CONFIG_PATH"),
            '--daemon', '--writepid', os.getenv("PID_FILE")
        ]
        process = subprocess.Popen(command)
        return jsonify({"status": "VPN Started"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def vpn_off():
    """Stops the OpenVPN process."""
    if not os.path.exists(os.getenv("PID_FILE")):
        return jsonify({"status": "VPN is not running."}), 409

    try:
        with open(os.getenv("PID_FILE"), 'r') as f:
            pid = f.read().strip()

        subprocess.run(['sudo', 'kill', pid], check=True)
        subprocess.run(['sudo', 'rm', os.getenv("PID_FILE")])

        return jsonify({"status": "VPN Stopped"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Failed to kill process or remove PID file: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def vpn_status():
    """Checks the status of the VPN."""
    vpn_is_on = False
    vpn_ip = None
    ip_result = subprocess.run(['curl', 'ifconfig.me'], capture_output=True, text=True)
    vpn_ip = ip_result.stdout.strip()

    if os.path.exists(os.getenv("PID_FILE")):
        try:
            result = subprocess.run(['ip', 'addr', 'show', 'tun0'], capture_output=True, text=True)
            if "tun0" in result.stdout:
                vpn_is_on = True

        except subprocess.CalledProcessError:
            vpn_is_on = False

    on_off = "ON" if vpn_is_on else "OFF"
    return jsonify({
        "status": "VPN is " + on_off,
        "ip_address": vpn_ip
    }), 200
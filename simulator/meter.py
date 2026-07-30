import asyncio
import json
import time
import random
import hmac
import hashlib
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

# --- Configuration ---
BROKER_HOST = "localhost"
BROKER_PORT = 1883
METERS = ["meter_001", "meter_002", "meter_003"]
PUBLISH_INTERVAL = 2.0
SECRET_KEY = b"super_secret_hackathon_key" # Shared secret for HMAC

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("[SYSTEM] Simulator successfully connected to MQTT Broker.")
    else:
        print(f"[ERROR] Failed to connect, return code {reason_code}")

def generate_telemetry(meter_id):
    voltage = random.uniform(235.0, 245.0)
    current = random.uniform(10.0, 50.0)
    
    payload = {
        "meter_id": meter_id,
        "timestamp": time.time(),
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "power": round(voltage * current, 2),
        "status": "OK"
    }
    
    # Create an HMAC-SHA256 signature of the data
    payload_str = json.dumps(payload, sort_keys=True)
    signature = hmac.new(SECRET_KEY, payload_str.encode(), hashlib.sha256).hexdigest()
    
    # Add signature to the final message
    payload["signature"] = signature
    return payload

async def run_meter(client, meter_id):
    print(f"[INIT] Starting secure simulation for {meter_id}...")
    while True:
        payload = generate_telemetry(meter_id)
        # Publish to the RAW topic so the gateway can intercept it
        topic = f"raw/telemetry/{meter_id}" 
        
        client.publish(topic, json.dumps(payload), qos=1)
        print(f"[PUBLISH] {meter_id} -> V:{payload['voltage']} | HMAC: {payload['signature'][:8]}...")
        
        await asyncio.sleep(PUBLISH_INTERVAL)

async def main():
    # Fixed DeprecationWarning by adding CallbackAPIVersion.VERSION2
    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="Simulator_Master", protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    
    try:
        client.connect(BROKER_HOST, BROKER_PORT)
        client.loop_start() 
    except Exception as e:
        print(f"[FATAL] Could not connect: {e}")
        return

    tasks = [run_meter(client, meter_id) for meter_id in METERS]
    print("\n--- Secure Smart Grid Simulator Running ---\n")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Simulation stopped gracefully.")
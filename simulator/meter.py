import paho.mqtt.client as mqtt
import json
import time
import random
import hmac
import hashlib

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC = "smart_grid/telemetry"
SECRET_KEY = b"secret_key_123"

# Initialize MQTT Client
client = mqtt.Client()
client.connect(BROKER, PORT, 60)

# Simulate an existing meter reading (e.g., 15,420 kWh already billed)
# This is exactly what a real utility company reads for your monthly bill.
cumulative_kWh = 15420.5000  

print("[SMART METER] Booting up... synchronizing with grid.")
print("[SMART METER] Beginning encrypted telemetry stream...\n")

while True:
    try:
        # 1. Simulate Grid Physics
        # Normal voltage in India/Europe is ~230V-240V.
        voltage = round(random.uniform(235.0, 245.0), 2)
        # Random current draw simulating household appliances turning on/off
        current = round(random.uniform(10.0, 50.0), 2)
        
        # 2. Calculate Power Consumption (The realistic part!)
        # Real power is Voltage * Current * Power Factor. 
        # Divided by 1000 to get kiloWatts (kW)
        power_factor = 0.95 
        power_kW = (voltage * current * power_factor) / 1000
        
        # Since we sleep for 1 second, the energy used in that second is kW / 3600 (seconds in an hour)
        cumulative_kWh += (power_kW / 3600)
        
        # 3. Build the Payload
        payload = {
            "meter_id": "meter_001",
            "voltage": voltage,
            "current": current,
            "power_kW": round(power_kW, 2),
            "units_kWh": round(cumulative_kWh, 5),
            "timestamp": int(time.time())
        }

        # 4. Cryptographic Signature (Anti-Tampering)
        # We sort keys so the JSON string is always identical for hashing
        message_string = json.dumps(payload, sort_keys=True)
        signature = hmac.new(SECRET_KEY, message_string.encode(), hashlib.sha256).hexdigest()
        
        # Add the signature to the final packet
        payload["signature"] = signature

        # 5. Transmit Data
        client.publish(TOPIC, json.dumps(payload))
        print(f"[\u26a1] V: {voltage}V | I: {current}A | Pwr: {round(power_kW, 2)}kW | Total Billed: {round(cumulative_kWh, 4)} Units (kWh)")
        
        time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SMART METER] Shutting down.")
        break
    except Exception as e:
        print(f"[ERROR] {e}")
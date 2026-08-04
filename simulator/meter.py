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

# Simulate a massive city block of 30 smart meters dynamically
NUM_METERS = 30
meters = {}
for i in range(1, NUM_METERS + 1):
    meter_id = f"meter_{i:03d}"
    # Give each meter a random starting kWh for realism
    meters[meter_id] = {"kWh": round(random.uniform(5000.0, 25000.0), 2)}

print(f"[SMART METER SIMULATOR] Booting up city grid with {NUM_METERS} meters...")
print(f"[SMART METER SIMULATOR] Beginning encrypted telemetry stream...\n")

while True:
    try:
        # Loop through each meter in the neighborhood
        for meter_id, data in meters.items():
            # 1. Simulate Grid Physics
            voltage = round(random.uniform(235.0, 245.0), 2)
            current = round(random.uniform(10.0, 50.0), 2)
            
            # 2. Calculate Power Consumption
            power_factor = 0.95 
            power_kW = (voltage * current * power_factor) / 1000
            
            data["kWh"] += (power_kW / 3600)
            
            # 3. Build the Payload
            payload = {
                "meter_id": meter_id,
                "voltage": voltage,
                "current": current,
                "power_kW": round(power_kW, 2),
                "units_kWh": round(data["kWh"], 5),
                "timestamp": int(time.time())
            }

            # 4. Cryptographic Signature
            message_string = json.dumps(payload, sort_keys=True)
            signature = hmac.new(SECRET_KEY, message_string.encode(), hashlib.sha256).hexdigest()
            payload["signature"] = signature

            # 5. Transmit Data
            client.publish(TOPIC, json.dumps(payload))
            print(f"[\u26a1] {meter_id} | V: {voltage}V | I: {current}A | Total: {round(data['kWh'], 2)} kWh")
        
        # Sleep for 1 second AFTER sending all 3, so each meter averages 1 msg/sec
        time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SMART METER] Shutting down.")
        break
    except Exception as e:
        print(f"[ERROR] {e}")
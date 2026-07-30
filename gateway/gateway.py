import json
import hmac
import hashlib
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

# --- Configuration ---
BROKER_HOST = "localhost"
BROKER_PORT = 1883
SECRET_KEY = b"super_secret_hackathon_key"

# Rate limiting dictionary: { "meter_id": last_timestamp }
RATE_LIMIT_STATE = {}
MAX_MESSAGES_PER_SECOND = 1.5 

def verify_hmac(payload):
    """Re-calculates the HMAC and compares it to the attached signature[cite: 1]."""
    provided_signature = payload.pop("signature", None)
    if not provided_signature:
        return False
        
    payload_str = json.dumps(payload, sort_keys=True)
    expected_signature = hmac.new(SECRET_KEY, payload_str.encode(), hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(expected_signature, provided_signature)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        meter_id = payload.get("meter_id", "UNKNOWN")
        current_time = time.time()
        
        # 1. Rate Limiting Check (DoS Protection)
        last_time = RATE_LIMIT_STATE.get(meter_id, 0)
        if current_time - last_time < (1.0 / MAX_MESSAGES_PER_SECOND):
            print(f"[DROP] DoS Flood detected from {meter_id}. Dropping message.")
            return
        RATE_LIMIT_STATE[meter_id] = current_time

        # 2. HMAC Authentication Check (Spoofing Protection)
        # We pass a copy so the original payload isn't modified during validation
        if not verify_hmac(payload.copy()):
            print(f"[DROP] Invalid HMAC Signature from {meter_id}. Unauthorized command blocked.")
            return

        # 3. Validation Passed -> Forward to the core grid
        forward_topic = f"grid/telemetry/{meter_id}"
        
        # Clean the signature out before forwarding to the IDS to save bandwidth
        clean_payload = payload.copy()
        clean_payload.pop("signature", None)
        
        client.publish(forward_topic, json.dumps(clean_payload), qos=1)
        print(f"[PASS] {meter_id} authenticated. Forwarding to core grid.")

    except json.JSONDecodeError:
        print("[DROP] Malformed JSON payload received.")

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("[SYSTEM] Secure Gateway connected. Listening for raw telemetry...")
        client.subscribe("raw/telemetry/#")
    else:
        print(f"[ERROR] Connection failed: {reason_code}")

if __name__ == "__main__":
    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="Secure_Gateway", protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(BROKER_HOST, BROKER_PORT)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Gateway shutting down.")
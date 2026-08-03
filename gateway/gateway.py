import paho.mqtt.client as mqtt
import json
import hmac
import hashlib
import time
from collections import defaultdict

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC = "smart_grid/telemetry"
SECRET_KEY = b"secret_key_123"

# Rate limiting database: tracks timestamps of messages per meter
message_history = defaultdict(list)
MAX_MESSAGES_PER_SECOND = 2  # A normal meter sends 1 per second.

def verify_signature(payload):
    """
    Verifies the cryptographic integrity of the payload to prevent 
    False Data Injection Attacks (FDIA).
    """
    # 1. Extract the signature provided by the sender
    provided_signature = payload.pop("signature", None)
    
    if not provided_signature:
        return False
        
    # 2. Recreate the string exactly how the smart meter built it
    # sort_keys=True ensures the order of the new units_kWh fields doesn't break the hash
    message_string = json.dumps(payload, sort_keys=True)
    
    # 3. Hash it with our Secret Key
    expected_signature = hmac.new(SECRET_KEY, message_string.encode(), hashlib.sha256).hexdigest()
    
    # 4. Securely compare them (compare_digest prevents timing attacks)
    return hmac.compare_digest(provided_signature, expected_signature)

def on_connect(client, userdata, flags, rc):
    print(f"[GATEWAY] Connected to Grid Broker (Port {PORT}).")
    client.subscribe(TOPIC)
    print(f"[GATEWAY] Active Firewalls: [HMAC Crypto-Check] & [Anti-DoS Rate Limiter]")
    print(f"[GATEWAY] Listening for incoming traffic...\n")

def on_message(client, userdata, msg):
    try:
        # Parse incoming telemetry
        payload = json.loads(msg.payload.decode())
        meter_id = payload.get("meter_id", "unknown_meter")
        
        # ==========================================
        # DEFENSE LAYER 1: Anti-DoS Rate Limiting
        # ==========================================
        current_time = time.time()
        
        # Clean up memory: remove message timestamps older than 1 second
        message_history[meter_id] = [t for t in message_history[meter_id] if current_time - t < 1.0]
        
        # If this meter has sent too many messages in the last second, drop it
        if len(message_history[meter_id]) >= MAX_MESSAGES_PER_SECOND:
            print(f"[DROP] DoS Flood detected from {meter_id}. Dropping message.")
            return
            
        # Record this message's timestamp for future checks
        message_history[meter_id].append(current_time)

        # ==========================================
        # DEFENSE LAYER 2: Cryptographic Identity
        # ==========================================
        # We pass a copy() of the payload so we don't accidentally delete the signature 
        # from the original dictionary if other parts of the system need it.
        if not verify_signature(payload.copy()):
            print(f"[DROP] Invalid HMAC Signature from {meter_id}. Unauthorized command blocked.")
            return

        # If it survives both checks, it is a valid, secure message!
        # In a real grid, the Gateway would forward this to a secure internal database.
        print(f"[\u2705 GATEWAY-PASS] Verified packet from {meter_id} | {payload.get('power_kW')} kW | {payload.get('units_kWh')} kWh")

    except json.JSONDecodeError:
        print("[DROP] Malformed JSON payload received.")
    except Exception as e:
        print(f"[GATEWAY ERROR] {e}")

# Initialize and run the Gateway
# Suppress the DeprecationWarning by explicitly setting the API version
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message

print("[GATEWAY] Booting up Secure Edge Gateway...")
client.connect(BROKER, PORT, 60)

# Keep listening forever, and catch Ctrl+C to shut down cleanly without errors
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[GATEWAY] Shutting down securely. Goodbye!")
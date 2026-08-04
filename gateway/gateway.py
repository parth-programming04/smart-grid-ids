import paho.mqtt.client as mqtt
import json
import hmac
import hashlib
import time
from collections import defaultdict
import sqlite3
import os

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC = "smart_grid/telemetry"
SECRET_KEY = b"secret_key_123"

# Lock the database to the main project folder (one level up from the gateway folder)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, "secure_grid.db")

# Rate limiting database: tracks timestamps of messages per meter
message_history = defaultdict(list)
MAX_MESSAGES_PER_SECOND = 2  # A normal meter sends 1 per second.

# ==========================================
# SECURE DATABASE SETUP (SQLite)
# ==========================================
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meter_id TEXT,
                voltage REAL,
                current REAL,
                power_kW REAL,
                units_kWh REAL,
                timestamp INTEGER
            )
        ''')
        conn.commit()

init_db()

def verify_signature(payload):
    """
    Verifies the cryptographic integrity of the payload to prevent 
    False Data Injection Attacks (FDIA).
    """
    provided_signature = payload.pop("signature", None)
    
    if not provided_signature:
        return False
        
    message_string = json.dumps(payload, sort_keys=True)
    expected_signature = hmac.new(SECRET_KEY, message_string.encode(), hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(provided_signature, expected_signature)

def on_connect(client, userdata, flags, rc):
    print(f"[GATEWAY] Connected to Grid Broker (Port {PORT}).")
    client.subscribe(TOPIC)
    print(f"[GATEWAY] Database Locked at: {DB_PATH}")
    print(f"[GATEWAY] Active Firewalls: [HMAC Crypto-Check] & [Anti-DoS Rate Limiter]")
    print(f"[GATEWAY] Listening for incoming traffic...\n")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        meter_id = payload.get("meter_id", "unknown_meter")
        
        # DEFENSE LAYER 1: Anti-DoS Rate Limiting
        current_time = time.time()
        message_history[meter_id] = [t for t in message_history[meter_id] if current_time - t < 1.0]
        
        if len(message_history[meter_id]) >= MAX_MESSAGES_PER_SECOND:
            print(f"[DROP] DoS Flood detected from {meter_id}. Dropping message.")
            return
            
        message_history[meter_id].append(current_time)

        # DEFENSE LAYER 2: Cryptographic Identity
        if not verify_signature(payload.copy()):
            print(f"[DROP] Invalid HMAC Signature from {meter_id}. Unauthorized command blocked.")
            return

        # SECURE STORAGE: Save to SQL Database using DB_PATH
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO telemetry (meter_id, voltage, current, power_kW, units_kWh, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                meter_id, 
                payload.get('voltage'), 
                payload.get('current'), 
                payload.get('power_kW'), 
                payload.get('units_kWh'), 
                payload.get('timestamp')
            ))
            conn.commit()

        print(f"[\u2705 GATEWAY-PASS] Verified & Saved packet from {meter_id} | {payload.get('power_kW')} kW | {payload.get('units_kWh')} kWh")

    except json.JSONDecodeError:
        print("[DROP] Malformed JSON payload received.")
    except Exception as e:
        print(f"[GATEWAY ERROR] {e}")

# Suppress the DeprecationWarning by explicitly setting the API version
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

print("[GATEWAY] Booting up Secure Edge Gateway...")
client.connect(BROKER, PORT, 60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[GATEWAY] Shutting down securely. Goodbye!")
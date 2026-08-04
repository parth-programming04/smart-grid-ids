import json
import warnings
import pandas as pd
from sklearn.ensemble import IsolationForest
import paho.mqtt.client as mqtt

# Suppress warnings for a clean terminal output
warnings.filterwarnings("ignore")

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "smart_grid/telemetry"  # <--- THIS WAS THE BUG! We fixed the topic here.

# AI Training Variables
training_data = []
TRAINING_SIZE = 500  # Increased to 500 to handle the massive volume of 30+ meters!
is_trained = False
model = IsolationForest(contamination=0.05, random_state=42)

def on_connect(client, userdata, flags, rc):
    print(f"[ML-IDS] Successfully connected to the Grid Broker!")
    print(f"[ML-IDS] Waiting for Smart Meter data on '{TOPIC}'...")

def on_message(client, userdata, msg):
    global is_trained, training_data, model
    
    try:
        payload = json.loads(msg.payload.decode())
        
        # Extract the physics data and the specific meter ID
        meter_id = payload.get("meter_id", "UNKNOWN")
        voltage = payload.get("voltage", 0.0)
        current = payload.get("current", 0.0)
        power = payload.get("power_kW", 0.0)
        units = payload.get("units_kWh", 0.0)
        
        # Phase 1: Data Collection & Training
        if not is_trained:
            training_data.append([voltage, current, power])
            print(f"[AI-TRAINING] Watching grid behavior... {len(training_data)}/{TRAINING_SIZE}")
            
            if len(training_data) >= TRAINING_SIZE:
                print("\n[AI-SYSTEM] Compiling physics profile. Training Machine Learning Model...")
                df = pd.DataFrame(training_data, columns=["voltage", "current", "power"])
                model.fit(df)
                is_trained = True
                print("[AI-SYSTEM] AI Active! Now hunting for stealth anomalies.\n")
            return

        # Phase 2: Live Intrusion Detection
        new_data = pd.DataFrame([[voltage, current, power]], columns=["voltage", "current", "power"])
        
        # Predict: 1 means Normal, -1 means Anomaly
        prediction = model.predict(new_data)[0]
        
        if prediction == -1:
            print(f"🚨 [AI ALERT] STEALTH ANOMALY FROM {meter_id}! Physics impossible! V:{voltage} I:{current} 🚨")
        else:
            print(f"✅ [AI-OK] {meter_id} is normal. V:{voltage:.1f} | I:{current:.1f} | Total: {units:.2f} kWh")
            
    except Exception as e:
        pass

# Use VERSION1 to avoid deprecation warnings
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

print("[ML-IDS] Booting up Machine Learning Intrusion Detection System...")
client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[ML-IDS] Shutting down AI securely.")
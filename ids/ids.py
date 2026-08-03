import paho.mqtt.client as mqtt
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from collections import deque
import warnings

# Suppress sklearn warnings for cleaner terminal output
warnings.filterwarnings("ignore")

# Configuration
BROKER = "localhost"
PORT = 1883
TOPIC = "smart_grid/telemetry"

# Data structures for the AI
# We will keep a rolling window of the last 50 readings to train the AI
TRAINING_WINDOW_SIZE = 50
data_buffer = deque(maxlen=TRAINING_WINDOW_SIZE)

# Initialize the Isolation Forest model
# contamination=0.05 means we expect roughly 5% of data might be anomalies
model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
is_model_trained = False

def on_connect(client, userdata, flags, rc):
    print(f"[ML-IDS] Connected to Smart Grid Broker with result code {rc}")
    client.subscribe(TOPIC)
    print(f"[ML-IDS] AI Agent listening to {TOPIC}... Waiting for data to train.")

def on_message(client, userdata, msg):
    global is_model_trained, model
    
    try:
        # Parse incoming telemetry
        payload = json.loads(msg.payload.decode())
        
        # We only care about voltage and current for physical anomaly detection
        voltage = payload.get("voltage")
        current = payload.get("current")
        units_kwh = payload.get("units_kWh")
        meter_id = payload.get("meter_id")
        
        if voltage is None or current is None:
            return
            
        # 1. Add new data to our rolling buffer
        data_buffer.append([voltage, current])
        
        # 2. Check if we have enough data to train/predict
        if len(data_buffer) < TRAINING_WINDOW_SIZE:
            print(f"[ML-IDS] Collecting training data... ({len(data_buffer)}/{TRAINING_WINDOW_SIZE})")
            return
            
        # 3. Train the model dynamically (Online Learning simulation)
        # In a real grid, this would be trained offline on months of data, 
        # but doing it live looks amazing for a hackathon demo!
        df = pd.DataFrame(list(data_buffer), columns=['voltage', 'current'])
        model.fit(df)
        is_model_trained = True
        
        # 4. Predict on the CURRENT incoming packet
        # reshape(1, -1) because we are predicting a single sample
        current_sample = np.array([[voltage, current]])
        prediction = model.predict(current_sample) # Returns 1 for normal, -1 for anomaly
        
        # 5. Evaluate the AI's prediction
        if prediction[0] == -1:
            print("\n" + "="*50)
            print(f"🚨 [AI ALERT] STEALTH ANOMALY DETECTED! 🚨")
            print(f"Target: {meter_id}")
            print(f"Suspicious Physics: Voltage={voltage}V, Current={current}A")
            print("="*50 + "\n")
        else:
            print(f"[ML-IDS] Normal -> {meter_id}: {voltage}V, {current}A | Billed: {units_kwh} kWh")

    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"[ML-IDS Error] {e}")

# Setup MQTT Client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("[ML-IDS] Booting up Machine Learning Intrusion Detection System...")
client.connect(BROKER, PORT, 60)

# Run forever
client.loop_forever()
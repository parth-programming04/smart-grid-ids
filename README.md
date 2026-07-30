# Smart Grid Intrusion Detection System (IDS)

A secure, simulated smart grid telemetry pipeline with built-in DoS and spoofing protection, built for our hackathon.

## What's Inside
* **`docker-compose.yml`**: Spun up an isolated Mosquitto MQTT broker.
* **`simulator/meter.py`**: Generates real-time, asynchronous telemetry (voltage, current) for 3 smart meters, secured with HMAC-SHA256 signatures.
* **`gateway/gateway.py`**: The middleware security checkpoint. Enforces rate-limiting (DoS protection) and verifies HMAC signatures before forwarding clean data to the main grid.

## How to Run It (Locally)

**1. Start the MQTT Broker**
Make sure Docker Desktop is running, then execute:
`docker compose up -d`

**2. Set up the Python Environment**
`python -m venv venv`
`venv\Scripts\Activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
`pip install paho-mqtt scikit-learn pandas fastapi uvicorn websockets redis`

**3. Run the Security Gateway**
Open a terminal, ensure your venv is active, and run:
`python gateway/gateway.py`

**4. Start the Simulator**
Open a *second* terminal, activate the venv, and run:
`python simulator/meter.py`
# Why Is It Blinking ?

### IoT Sensor Data Pipeline & Motorsport Telemetry Analytics Dashboard

Have you ever looked at a vehicle dashboard full of blinking warning lights and wondered exactly *why*? 

**Why Is It Blinking?** is an end-to-end data engineering and analytics platform. It ingests high-fidelity physical telemetry data (such as throttle input, sequential gearing, braking pressure, and engine RPM curves), processes it through a local relational database, and streams it into an interactive web interface for real-time diagnostics and anomaly tracking.

---

## System Architecture

* **Data Source:** High-fidelity motorsport data stream mimicking real-world vehicle telemetry profiles (coherent acceleration curves, sequential downshifts, and braking pressure spikes).
* **Ingestion Backend:** Built using **FastAPI** to handle asynchronous concurrent telemetry payloads with low latency.
* **Storage Layer:** Relational **MySQL** storage designed to cache historical laps, manage indices, and serve time-series tracking data.
* **Analytics Layer:** A lightweight interactive analytics engine displaying live time-series tracking, mechanical status operational gauges, and sequential rev-matching indicators.
* **CI/CD Pipeline:** Automated GitHub Actions workflows that run `pytest` suites to validate schema conformity and verify endpoints before deployment.

---


### Prerequisites
* Python 3.10+
* requirements.txt
* MySQL Server

<!--
### Installation & Local Launch

```bash
# 1. Clone the repository
git clone [https://github.com/your-username/WhyIsItBlinking.git](https://github.com/your-username/WhyIsItBlinking.git)
cd WhyIsItBlinking

# 2. Set up an isolated virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 3. Install core framework requirements
pip install -r requirements.txt

# 4. Set up your environment variables (.env)
cat <<EOF > .env
DATABASE_URL="mysql+mysqlconnector://root:password@localhost/telemetry_db"
PORT=8000
HOST=0.0.0.0
EOF

# 5. Boot the FastAPI web server manually
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

-->

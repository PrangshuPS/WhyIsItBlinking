
# Why is it Blinking?
Ever wated to know why your dashboard was full of blinking LEDs but you could know why. 

## IoT Sensor Data Pipeline and Analytics Dashboard

An end-to-end data engineering and analytics platform that ingests real-time telematics from an ESP32 sensor node, processes data through an automated ETL pipeline, and visualizes system health metrics on an interactive web dashboard.

## System Architecture

1. **Data Source**: ESP32 microcontroller reading environmental sensors (DHT22/BME280) and streaming structured JSON payloads over HTTP POST/MQTT.
2. **Ingestion & Storage**: A Python ingestion script processes the stream and writes concurrently to a local SQLite database for edge processing and Firebase for cloud availability.
3. **ETL Pipeline**: Python and Pandas scripts handle data cleaning, compute rolling and hourly averages, and execute statistical anomaly detection to flag critical thresholds.
4. **Analytics Layer**: A Streamlit dashboard utilizing Plotly for live time-series tracking, operational gauges, predictive maintenance flags, and anomaly notifications.
5. **Automation**: CI/CD workflows managed via GitHub Actions to automatically run test suites, validate data schemas using pytest, and trigger ETL tasks.

## Containerized Deployment & CI/CD

This application is containerized with Docker and Docker Compose, supporting multi-architecture builds (`linux/amd64` and `linux/arm64`) to run seamlessly on standard laptops and single-board computers like the **Raspberry Pi 5**.

### Prerequisites

To run this application, you only need:
1. **Docker** and **Docker Compose** installed on your host.
2. An active internet connection (for initial OpenF1 API metadata sync, though cached files are provided).

---

## Raspberry Pi 5 Setup & Hosting Guide

Follow these steps to deploy and host the application on a Raspberry Pi 5:

### 1. Install Docker on Raspberry Pi OS
Open the terminal on your Raspberry Pi and run the convenience script:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Add your user to the `docker` group to run docker without `sudo` (requires a re-login or reboot to apply):
```bash
sudo usermod -aG docker $USER
newgrp docker
```

Verify the installation:
```bash
docker --version
docker compose version
```

### 2. Pull the Branch & Configure Environment
Clone your repository and navigate into the folder:
```bash
git clone <your-github-repo-url> WhyIsItBlinking
cd WhyIsItBlinking
```

Create/edit the `.env` file for docker configuration:
```bash
cp .env.example .env  # Or edit your existing .env file
```
Ensure your environment variables are configured correctly. Inside Docker Compose, the database credentials will be automatically passed, and the app connects to the database container (`db`) without requiring you to manually install MariaDB on the host!

### 3. Run the Application
Start the services in detached (background) mode:
```bash
docker compose up -d
```
Docker Compose will automatically:
- Launch a MariaDB database container and persist its data to a Docker volume.
- Build the FastAPI application image (or pull it from GHCR if deploying via CI/CD).
- Wait for the MariaDB service to be healthy.
- Initialize the database tables (`sensor_readings` and `anomalies`).
- Start the web dashboard.

Access the dashboard in your web browser at:
```
http://<your-raspberry-pi-ip>:8000
```
*(Use `hostname -I` on your Pi to find its IP address.)*

### 4. Stopping and Managing
- To view logs: `docker compose logs -f`
- To stop the services: `docker compose down`
- To rebuild/restart: `docker compose up -d --build`

---

## OpenF1 API Caching & Rate Limiting

The OpenF1 API enforces a **limit of 30 requests per hour**. To respect this limit and ensure high availability, the app implements:
1. **Persistent SQLite Caching**: All historical responses (which are static and do not change) are saved to `openf1_cache.db`. If a query has been requested before, it is loaded instantly from the disk without consuming your API quota.
2. **Hour-Rolling Rate Limiter**: The app monitors live outgoing requests. If you attempt more than 30 uncached requests within a 60-minute window, the app will log a warning and block further live API calls, protecting your connection from being blacklisted by the API provider.
3. **Startup Pre-caching**: A pre-populated cache is included in this repository so that the default track, driver, and telemetry data load instantly upon initial launch without hitting the live API at all.

---

## CI/CD Pipeline (GitHub Actions)

A GitHub Actions workflow is located at `.github/workflows/deploy.yml`. When you push changes to the `main` branch, the runner automatically:
1. Sets up QEMU for ARM64 hardware emulation.
2. Builds a multi-architecture Docker image (`linux/amd64` and `linux/arm64`).
3. Publishes the image to **GitHub Container Registry (GHCR)**.

This allows your Raspberry Pi 5 to pull pre-compiled, optimized ARM64 Docker images instantly instead of compiling large packages (like pandas/scikit-learn) locally, speeding up updates.
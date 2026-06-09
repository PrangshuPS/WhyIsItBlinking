
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

Still under preocess 
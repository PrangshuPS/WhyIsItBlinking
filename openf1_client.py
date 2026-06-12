from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import threading
from statistics import mean
from typing import Any
import sqlite3
import json
import time
import os

import requests


BASE_URL = "https://api.openf1.org/v1"
TIMEOUT = 15
CURRENT_YEAR = datetime.utcnow().year
TRACK_YEARS = range(2023, CURRENT_YEAR + 1)

_session = requests.Session()
_state_lock = threading.RLock()
_current_selection: dict[str, Any] | None = None
_current_samples: list[dict[str, Any]] = []
_current_index = 0

CACHE_DB = os.environ.get("OPENF1_CACHE_DB", "openf1_cache.db")

def init_cache_db():
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                url TEXT,
                params TEXT,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (url, params)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_log (
                timestamp REAL
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing SQLite cache DB: {e}")

# Run initialization immediately on load
init_cache_db()

def get_cached_response(path: str, params: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        params_str = json.dumps(params, sort_keys=True) if params else "{}"
        cursor.execute("SELECT response FROM api_cache WHERE url = ? AND params = ?", (path, params_str))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception as e:
        print(f"Error reading from OpenF1 cache: {e}")
    return None

def save_to_cache(path: str, params: dict[str, Any] | None, response_data: list[dict[str, Any]]):
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        params_str = json.dumps(params, sort_keys=True) if params else "{}"
        response_str = json.dumps(response_data)
        cursor.execute(
            "INSERT OR REPLACE INTO api_cache (url, params, response) VALUES (?, ?, ?)",
            (path, params_str, response_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving to OpenF1 cache: {e}")

def log_request():
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO request_log (timestamp) VALUES (?)", (time.time(),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging request to rate limiter: {e}")

def check_rate_limit() -> bool:
    try:
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        one_hour_ago = time.time() - 3600
        # Clean up old logs older than 1 hour
        cursor.execute("DELETE FROM request_log WHERE timestamp < ?", (one_hour_ago,))
        conn.commit()
        # Count requests in the last hour
        cursor.execute("SELECT COUNT(*) FROM request_log")
        count = cursor.fetchone()[0]
        conn.close()
        return count < 30
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        return True

def _request(path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    # Check cache first
    cached = get_cached_response(path, params)
    if cached is not None:
        return cached

    # Check rate limit before making a live request
    if not check_rate_limit():
        raise RuntimeError("OpenF1 API rate limit (30 requests/hour) exceeded. Refusing live API request.")

    # Log request to rate limiter
    log_request()

    response = _session.get(f"{BASE_URL}/{path.lstrip('/')}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    data = payload if isinstance(payload, list) else []
    
    # Save to cache
    save_to_cache(path, params, data)
    return data


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.min
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.min


def _session_priority(session_row: dict[str, Any]) -> tuple[int, datetime, int]:
    session_name = str(session_row.get("session_name", "")).lower()
    if "race" in session_name:
        priority = 0
    elif "qualifying" in session_name:
        priority = 1
    elif "sprint" in session_name:
        priority = 2
    else:
        priority = 3
    return (priority, _parse_datetime(session_row.get("date_end")), int(session_row.get("session_key") or 0))


def _pick_representative_session(session_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not session_rows:
        return None
    return sorted(session_rows, key=_session_priority)[0]


def _numeric_values(values: list[Any]) -> list[float]:
    cleaned = []
    for value in values:
        if value is None:
            continue
        try:
            cleaned.append(float(value))
        except (TypeError, ValueError):
            continue
    return cleaned


@lru_cache(maxsize=1)
def get_track_catalog() -> list[dict[str, Any]]:
    tracks: dict[int, dict[str, Any]] = {}
    for year in TRACK_YEARS:
        try:
            sessions = _request("sessions", {"year": year})
        except requests.RequestException:
            continue

        for row in sessions:
            meeting_key = row.get("meeting_key")
            if meeting_key is None:
                continue

            meeting_key = int(meeting_key)
            existing = tracks.get(meeting_key)
            candidate = {
                "meeting_key": meeting_key,
                "session_key": row.get("session_key"),
                "year": row.get("year", year),
                "country_name": row.get("country_name"),
                "location": row.get("location"),
                "circuit_short_name": row.get("circuit_short_name"),
                "meeting_name": row.get("meeting_name"),
                "session_name": row.get("session_name"),
                "date_start": row.get("date_start"),
                "date_end": row.get("date_end"),
            }

            if existing is None:
                tracks[meeting_key] = candidate
                continue

            current_rank = _session_priority(existing)
            candidate_rank = _session_priority(candidate)
            if candidate_rank < current_rank:
                tracks[meeting_key] = candidate

    ordered_tracks = sorted(
        tracks.values(),
        key=lambda item: (
            -int(item.get("year") or 0),
            str(item.get("country_name") or ""),
            str(item.get("meeting_name") or ""),
        ),
    )
    return ordered_tracks


def get_driver_catalog(meeting_key: int) -> list[dict[str, Any]]:
    try:
        meeting_sessions = _request("sessions", {"meeting_key": meeting_key})
    except requests.RequestException:
        return []

    session_row = _pick_representative_session(meeting_sessions)
    if not session_row:
        return []

    try:
        drivers = _request("drivers", {"session_key": session_row.get("session_key")})
    except requests.RequestException:
        return []

    seen: set[int] = set()
    catalog: list[dict[str, Any]] = []
    for row in drivers:
        driver_number = row.get("driver_number")
        if driver_number is None:
            continue
        driver_number = int(driver_number)
        if driver_number in seen:
            continue
        seen.add(driver_number)
        catalog.append(
            {
                "driver_number": driver_number,
                "full_name": row.get("full_name") or row.get("broadcast_name") or row.get("name_acronym") or f"Driver {driver_number}",
                "team_name": row.get("team_name"),
                "name_acronym": row.get("name_acronym"),
                "session_key": row.get("session_key"),
            }
        )

    return sorted(catalog, key=lambda item: item["driver_number"])


def get_historical_analysis(meeting_key: int, driver_number: int) -> dict[str, Any]:
    try:
        meeting_sessions = _request("sessions", {"meeting_key": meeting_key})
    except requests.RequestException as exc:
        return {"status": "error", "message": f"Unable to load OpenF1 sessions: {exc}"}

    session_row = _pick_representative_session(meeting_sessions)
    if not session_row:
        return {"status": "error", "message": "No OpenF1 session found for the selected track."}

    session_key = session_row.get("session_key")
    if session_key is None:
        return {"status": "error", "message": "Selected track does not expose a valid session key."}

    session_key = int(session_key)
    driver_number = int(driver_number)

    try:
        driver_rows = _request("drivers", {"session_key": session_key, "driver_number": driver_number})
    except requests.RequestException:
        driver_rows = []
    driver_row = driver_rows[0] if driver_rows else {}

    car_params: dict[str, Any] = {"session_key": session_key, "driver_number": driver_number}
    if session_row.get("date_start"):
        car_params["date>="] = session_row.get("date_start")
    if session_row.get("date_end"):
        car_params["date<="] = session_row.get("date_end")

    try:
        car_data = _request("car_data", car_params)
    except requests.RequestException as exc:
        return {"status": "error", "message": f"Unable to load OpenF1 car data: {exc}"}

    if not car_data:
        return {
            "status": "no_data",
            "message": "OpenF1 returned no car telemetry for the selected track and driver.",
            "metadata": {
                "meeting_key": meeting_key,
                "session_key": session_key,
                "driver_number": driver_number,
                "track_name": session_row.get("circuit_short_name") or session_row.get("location") or session_row.get("meeting_name"),
            },
        }

    recent_car_data = car_data[-360:]
    timestamps = [row.get("date") for row in recent_car_data]
    rpm_values = _numeric_values([row.get("rpm") for row in recent_car_data])
    speed_values = _numeric_values([row.get("speed") for row in recent_car_data])
    throttle_values = _numeric_values([row.get("throttle") for row in recent_car_data])
    brake_values = _numeric_values([row.get("brake") for row in recent_car_data])
    gear_values = _numeric_values([row.get("n_gear") for row in recent_car_data])

    try:
        laps = _request("laps", {"session_key": session_key, "driver_number": driver_number})
    except requests.RequestException:
        laps = []

    try:
        weather_rows = _request("weather", {"session_key": session_key})
    except requests.RequestException:
        weather_rows = []

    lap_summary = []
    for lap in laps[-12:]:
        lap_summary.append(
            {
                "lap_number": lap.get("lap_number"),
                "lap_duration": lap.get("lap_duration"),
                "st_speed": lap.get("st_speed"),
                "i1_speed": lap.get("i1_speed"),
                "i2_speed": lap.get("i2_speed"),
                "date_start": lap.get("date_start"),
            }
        )

    def _avg(values: list[float]) -> float | None:
        return round(mean(values), 1) if values else None

    summary = {
        "samples": len(recent_car_data),
        "avg_speed": _avg(speed_values),
        "max_speed": round(max(speed_values), 1) if speed_values else None,
        "avg_rpm": _avg(rpm_values),
        "max_rpm": round(max(rpm_values), 1) if rpm_values else None,
        "avg_throttle": _avg(throttle_values),
        "max_throttle": round(max(throttle_values), 1) if throttle_values else None,
        "avg_brake": _avg(brake_values),
        "avg_gear": _avg(gear_values),
        "lap_count": len(laps),
        "fastest_lap": min((lap.get("lap_duration") for lap in laps if lap.get("lap_duration") is not None), default=None),
    }

    weather = weather_rows[-1] if weather_rows else {}

    return {
        "status": "ok",
        "metadata": {
            "meeting_key": meeting_key,
            "session_key": session_key,
            "session_name": session_row.get("session_name"),
            "session_type": session_row.get("session_type"),
            "year": session_row.get("year"),
            "track_name": session_row.get("circuit_short_name") or session_row.get("location") or session_row.get("meeting_name"),
            "meeting_name": session_row.get("meeting_name"),
            "country_name": session_row.get("country_name"),
            "driver_number": driver_number,
            "driver_name": driver_row.get("full_name") or driver_row.get("broadcast_name") or f"Driver {driver_number}",
            "team_name": driver_row.get("team_name"),
            "name_acronym": driver_row.get("name_acronym"),
            "date_start": session_row.get("date_start"),
            "date_end": session_row.get("date_end"),
        },
        "summary": summary,
        "series": {
            "timestamps": timestamps,
            "rpm": [row.get("rpm") for row in recent_car_data],
            "speed": [row.get("speed") for row in recent_car_data],
            "throttle": [row.get("throttle") for row in recent_car_data],
            "brake": [row.get("brake") for row in recent_car_data],
            "gear": [row.get("n_gear") for row in recent_car_data],
            "drs": [row.get("drs") for row in recent_car_data],
        },
        "laps": lap_summary,
        "weather": {
            "air_temperature": weather.get("air_temperature"),
            "track_temperature": weather.get("track_temperature"),
            "humidity": weather.get("humidity"),
            "wind_speed": weather.get("wind_speed"),
            "rainfall": weather.get("rainfall"),
        },
    }


def _derive_series_sample(index: int, analysis: dict[str, Any]) -> dict[str, Any]:
    series = analysis.get("series", {})
    weather = analysis.get("weather", {})

    rpm = series.get("rpm", [])
    speed = series.get("speed", [])
    throttle = series.get("throttle", [])
    brake = series.get("brake", [])
    gear = series.get("gear", [])
    drs = series.get("drs", [])
    timestamps = series.get("timestamps", [])

    sample_speed = float(speed[index] or 0)
    sample_throttle = float(throttle[index] or 0)
    sample_brake = float(brake[index] or 0)
    sample_rpm = float(rpm[index] or 0)
    sample_gear = gear[index] if index < len(gear) else None
    sample_time = timestamps[index] if index < len(timestamps) else None

    track_temp = weather.get("track_temperature")
    air_temp = weather.get("air_temperature")

    coolant_temp = round((float(track_temp) if track_temp is not None else 92.0) + (sample_speed / 30.0) + (sample_throttle / 18.0), 1)
    engine_load = round(min(100.0, max(0.0, sample_throttle * 0.82 + sample_speed * 0.08 + sample_brake * 0.05)), 1)
    fuel_pressure = round(max(20.0, 48.0 - sample_brake * 0.04 + sample_throttle * 0.03), 1)
    intake_temp = round((float(air_temp) if air_temp is not None else 26.0) + 6.0 + sample_throttle * 0.05, 1)
    battery_voltage = round(13.2 + (sample_speed / 1000.0) - (sample_brake / 200.0), 2)

    return {
        "timestamp": sample_time,
        "rpm": round(sample_rpm, 1),
        "speed": round(sample_speed, 1),
        "coolant_temp": coolant_temp,
        "throttle": round(sample_throttle, 1),
        "engine_load": engine_load,
        "fuel_pressure": fuel_pressure,
        "intake_temp": intake_temp,
        "battery_voltage": battery_voltage,
        "brake": round(sample_brake, 1),
        "gear": sample_gear,
        "drs": drs[index] if index < len(drs) else None,
        "track_temperature": track_temp,
        "air_temperature": air_temp,
        "driver_number": analysis.get("metadata", {}).get("driver_number"),
        "driver_name": analysis.get("metadata", {}).get("driver_name"),
        "team_name": analysis.get("metadata", {}).get("team_name"),
        "track_name": analysis.get("metadata", {}).get("track_name"),
        "meeting_key": analysis.get("metadata", {}).get("meeting_key"),
        "session_key": analysis.get("metadata", {}).get("session_key"),
        "source": "openf1",
    }


def _set_active_series(analysis: dict[str, Any]) -> dict[str, Any]:
    samples = []
    total = len(analysis.get("series", {}).get("timestamps", []))
    if total:
        step = max(1, total // 360)
        for index in range(0, total, step):
            samples.append(_derive_series_sample(index, analysis))

    with _state_lock:
        global _current_selection, _current_samples, _current_index
        _current_selection = {
            "meeting_key": analysis["metadata"]["meeting_key"],
            "driver_number": analysis["metadata"]["driver_number"],
            "track_name": analysis["metadata"]["track_name"],
            "session_key": analysis["metadata"]["session_key"],
            "driver_name": analysis["metadata"].get("driver_name"),
            "team_name": analysis["metadata"].get("team_name"),
            "session_name": analysis["metadata"].get("session_name"),
            "year": analysis["metadata"].get("year"),
            "summary": analysis.get("summary", {}),
            "weather": analysis.get("weather", {}),
            "laps": analysis.get("laps", []),
        }
        _current_samples = samples
        _current_index = 0

    return get_current_state()


def prepare_selection(meeting_key: int, driver_number: int) -> dict[str, Any]:
    analysis = get_historical_analysis(meeting_key, driver_number)
    if analysis.get("status") != "ok":
        return analysis
    return _set_active_series(analysis)


def ensure_default_selection() -> dict[str, Any]:
    with _state_lock:
        if _current_samples:
            return get_current_state()

    tracks = get_track_catalog()
    if not tracks:
        return {"status": "no_data", "message": "OpenF1 track catalog is empty."}

    for track in tracks:
        meeting_key = track.get("meeting_key")
        if meeting_key is None:
            continue
        drivers = get_driver_catalog(int(meeting_key))
        if not drivers:
            continue
        return prepare_selection(int(meeting_key), int(drivers[0]["driver_number"]))

    return {"status": "no_data", "message": "OpenF1 did not return a usable default track/driver."}


def next_sample() -> dict[str, Any]:
    with _state_lock:
        global _current_index
        if not _current_samples:
            pass
        elif _current_index < len(_current_samples):
            sample = dict(_current_samples[_current_index])
            _current_index = (_current_index + 1) % len(_current_samples)
            sample["selected"] = _current_selection.copy() if _current_selection else {}
            return sample

    default_state = ensure_default_selection()
    if default_state.get("status") != "ok":
        return {}
    return next_sample()


def get_current_state() -> dict[str, Any]:
    with _state_lock:
        if not _current_selection:
            return {"status": "idle", "message": "No OpenF1 selection loaded yet."}
        state = dict(_current_selection)
        state["status"] = "ok"
        state["sample_count"] = len(_current_samples)
        state["next_index"] = _current_index
        return state


def get_current_samples() -> list[dict[str, Any]]:
    with _state_lock:
        return [dict(sample) for sample in _current_samples]
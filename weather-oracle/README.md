# WeatherOracle

> Real-time global weather data on GenLayer — with AI-powered danger alerts, city comparisons, and threshold monitoring.

---

## Overview

WeatherOracle is a GenLayer Intelligent Contract that fetches live weather conditions for 13 cities worldwide using the Open-Meteo API. Each fetch goes through five-validator consensus before being cached on-chain. Beyond raw weather data, the contract uses GenLayer's native LLM integration to generate danger alerts, compare cities, and produce global briefings — capabilities no traditional oracle can offer.

Open-Meteo requires no API key and is confirmed compatible with GenLayer validators.

---

## Supported Cities

London · New York · Lagos · Tokyo · Paris · Dubai · Singapore · Nairobi · Port Harcourt · Abuja · Berlin · Sydney · Toronto

---

## Methods

### Write Methods
Fetch live data and write to chain. Require gas and validator consensus.

| Method | Parameters | Description |
|---|---|---|
| `fetch_weather` | `city: str` | Fetch current conditions for one city |
| `fetch_multiple` | `cities: list` | Fetch several cities in one transaction |
| `fetch_forecast` | `city: str, days: int` | Fetch a multi-day forecast |
| `generate_alert` | `city: str` | AI danger assessment: safe / caution / danger |
| `generate_summary` | — | AI global briefing across all cached cities |
| `compare_cities` | `city1: str, city2: str` | AI head-to-head comparison of two cities |

### Read Methods
Read from cache. No gas required.

| Method | Parameters | Description |
|---|---|---|
| `read_weather` | `city: str` | Cached conditions for one city |
| `read_all` | — | All cached weather data |
| `list_locations` | — | All supported city names |
| `hottest_city` | — | City with the highest temperature |
| `coldest_city` | — | City with the lowest temperature |
| `humidity_alert` | `threshold: int` | Cities above a humidity percentage |
| `wind_alert` | `threshold: int` | Cities above a wind speed (km/h) |
| `freshness` | `city: str` | Whether a city has been fetched |
| `cache_report` | — | Full cache status for all cities |

---

## Deploying

1. Open [studio.genlayer.com](https://studio.genlayer.com)
2. Paste `contract.py` into the editor
3. Click **Deploy new instance** — no parameters needed
4. Wait for FINALIZED

---

## Testing

```
# Fetch one city
fetch_weather("Lagos")

# Fetch several cities at once
fetch_multiple(["Lagos", "London", "Tokyo"])

# Multi-day forecast
fetch_forecast("Lagos", 5)

# AI danger alert (needs cached weather first)
generate_alert("Lagos")
# Returns: {"alert_level": "safe", "reason": "...", "recommendation": "..."}

# Compare two cities (both must be cached)
compare_cities("Lagos", "London")

# Threshold monitoring
humidity_alert(80)
wind_alert(50)

# Extremes
hottest_city()
coldest_city()
```

---

## Data Source

Open-Meteo (`api.open-meteo.com`) — free, no API key, confirmed working with GenLayer validators. Measurements are taken at 2 metres above ground level and may differ slightly from local station readings.

---

## How Consensus Works

Weather fetches use `prompt_comparative` with tolerances of 1°C temperature, 5% humidity, and 3 km/h wind speed — accounting for natural variation between validator fetches moments apart.

AI alerts and comparisons use `prompt_comparative` with a condition matching on alert level or trend direction, allowing flexibility in wording while ensuring validators agree on the conclusion.

---

## State

| Variable | Type | Purpose |
|---|---|---|
| `store` | `str` | JSON cache of all weather data |
| `pulse` | `str` | Tracks which cities have been fetched |
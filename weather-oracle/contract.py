# { "Depends": "py-genlayer:test" }

from genlayer import *
import json
import typing


LOCATIONS = {
    "London":        ("51.5074",  "-0.1278"),
    "New York":      ("40.7128",  "-74.0060"),
    "Lagos":         ("6.5244",   "3.3792"),
    "Tokyo":         ("35.6762",  "139.6503"),
    "Paris":         ("48.8566",  "2.3522"),
    "Dubai":         ("25.2048",  "55.2708"),
    "Singapore":     ("1.3521",   "103.8198"),
    "Nairobi":       ("1.2921",   "36.8219"),
    "Port Harcourt": ("4.8156",   "7.0498"),
    "Abuja":         ("9.0765",   "7.3986"),
    "Berlin":        ("52.5200",  "13.4050"),
    "Sydney":        ("-33.8688", "151.2093"),
    "Toronto":       ("43.6532",  "-79.3832"),
}


def _pull_current(city: str, lat: str, lon: str) -> str:
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"wind_speed_10m,precipitation,weathercode"
            f"&timezone=auto"
        )
        raw = gl.nondet.web.render(url, mode="text")
        if not raw or raw.strip() in ["null", "", "null\n"]:
            return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})
        data = json.loads(raw)
        if "current" not in data:
            return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})
        current = data["current"]
        return json.dumps({
            "city":        city,
            "temperature": current["temperature_2m"],
            "humidity":    current["relative_humidity_2m"],
            "wind_speed":  current["wind_speed_10m"],
            "rain":        current["precipitation"],
            "weathercode": current["weathercode"],
            "unit":        data["current_units"]["temperature_2m"],
            "status":      "ok",
        }, sort_keys=True)
    except Exception:
        return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})


class WeatherOracle(gl.Contract):

    store:   str
    pulse:   str

    def __init__(self):
        self.store = "{}"
        self.pulse = "{}"

    # ── FETCH ───────────────────────────────────────────────────────

    @gl.public.write
    def fetch_weather(self, city: str) -> typing.Any:
        if city not in LOCATIONS:
            raise gl.vm.UserError(city + " is not supported. Call list_locations to see supported cities.")
        lat, lon = LOCATIONS[city]

        def fetch() -> str:
            return _pull_current(city, lat, lon)

        fresh              = gl.eq_principle.prompt_comparative(
            fetch,
            "The outputs represent weather data for the same city. "
            "They are equivalent if both show an API error, "
            "or if temperature is within 1 degree, humidity within 5%, "
            "and wind speed within 3 km/h of each other."
        )
        data               = json.loads(self.store)
        data[city]         = json.loads(fresh)
        self.store         = json.dumps(data, sort_keys=True)
        hb                 = json.loads(self.pulse)
        hb[city]           = "updated"
        self.pulse         = json.dumps(hb, sort_keys=True)

    @gl.public.write
    def fetch_multiple(self, cities: list) -> typing.Any:
        data = json.loads(self.store)
        hb   = json.loads(self.pulse)
        for city in cities:
            if city not in LOCATIONS:
                data[city] = {"error": city + " is not supported.", "status": "unsupported"}
                continue
            lat, lon = LOCATIONS[city]
            def fetch() -> str:
                return _pull_current(city, lat, lon)
            fresh      = gl.eq_principle.prompt_comparative(
                fetch,
                "The outputs represent weather data for the same city. "
                "They are equivalent if both show an API error, "
                "or if temperature is within 1 degree, humidity within 5%, "
                "and wind speed within 3 km/h of each other."
            )
            data[city] = json.loads(fresh)
            hb[city]   = "updated"
        self.store = json.dumps(data, sort_keys=True)
        self.pulse = json.dumps(hb, sort_keys=True)

    @gl.public.write
    def fetch_forecast(self, city: str, days: int) -> typing.Any:
        if city not in LOCATIONS:
            raise gl.vm.UserError(city + " is not supported.")
        lat, lon = LOCATIONS[city]
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,weathercode,wind_speed_10m_max"
            f"&timezone=auto"
            f"&forecast_days={days}"
        )
        def fetch() -> str:
            try:
                raw = gl.nondet.web.render(url, mode="text")
                if not raw or raw.strip() in ["null", "", "null\n"]:
                    return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})
                data = json.loads(raw)
                if "daily" not in data:
                    return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})
                daily    = data["daily"]
                forecast = []
                for i in range(len(daily["time"])):
                    forecast.append({
                        "date":        daily["time"][i],
                        "temp_max":    daily["temperature_2m_max"][i],
                        "temp_min":    daily["temperature_2m_min"][i],
                        "rain_total":  daily["precipitation_sum"][i],
                        "wind_max":    daily["wind_speed_10m_max"][i],
                        "weathercode": daily["weathercode"][i],
                    })
                return json.dumps({"city": city, "days": days, "forecast": forecast, "status": "ok"}, sort_keys=True)
            except Exception:
                return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})

        fresh              = gl.eq_principle.prompt_comparative(
            fetch,
            "The outputs represent a weather forecast for the same city. "
            "They are equivalent if both show an API error, "
            "or if temperatures are within 2 degrees and dates match exactly."
        )
        data               = json.loads(self.store)
        if city not in data:
            data[city]     = {}
        if isinstance(data[city], dict):
            data[city]["forecast"] = json.loads(fresh)
        else:
            data[city] = {"forecast": json.loads(fresh)}
        self.store = json.dumps(data, sort_keys=True)

    # ── AI ─────────────────────────────────────────────────────────

    @gl.public.write
    def generate_alert(self, city: str) -> typing.Any:
        data = json.loads(self.store)
        if city not in data:
            raise gl.vm.UserError(city + " not cached. Call fetch_weather first.")
        weather = data[city]
        if weather.get("status") != "ok":
            return

        def analyze() -> str:
            prompt = (
                f"Analyze this weather data for {city} and determine if conditions are dangerous:\n\n"
                f"{json.dumps(weather)}\n\n"
                f"Consider: temperature extremes, high winds above 60 km/h, "
                f"heavy rain above 10mm, severe weathercodes (95-99).\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{\"city\": \"{city}\", '
                f'\"alert_level\": \"safe\" or \"caution\" or \"danger\", '
                f'\"reason\": \"one sentence explanation\", '
                f'\"recommendation\": \"one sentence advice\"}}'
            )
            return gl.nondet.exec_prompt(prompt)

        alert              = gl.eq_principle.prompt_comparative(
            analyze,
            "Both outputs assess the same weather conditions. "
            "They are equivalent if they assign the same alert level."
        )
        data[city]["alert"] = json.loads(alert)
        self.store          = json.dumps(data, sort_keys=True)

    @gl.public.write
    def generate_summary(self) -> typing.Any:
        data = json.loads(self.store)
        if not data:
            return

        def summarize() -> str:
            prompt = (
                f"You are a professional meteorologist. Based on this weather data "
                f"from cities around the world, write a concise two-sentence global "
                f"weather briefing:\n\n{json.dumps(data)}\n\n"
                f"Respond with only the briefing, nothing else."
            )
            return gl.nondet.exec_prompt(prompt)

        summary          = gl.eq_principle.prompt_comparative(
            summarize,
            "Both outputs summarize the same global weather conditions. "
            "They are equivalent if they mention the same key trends."
        )
        data["summary"]  = summary
        self.store       = json.dumps(data, sort_keys=True)

    @gl.public.write
    def compare_cities(self, city1: str, city2: str) -> typing.Any:
        data = json.loads(self.store)
        if city1 not in data or city2 not in data:
            raise gl.vm.UserError("Both cities must be cached first.")
        w1 = data[city1]
        w2 = data[city2]
        if w1.get("status") != "ok" or w2.get("status") != "ok":
            return

        def analyze() -> str:
            prompt = (
                f"Compare the weather conditions of {city1} and {city2}:\n\n"
                f"{city1}: {json.dumps(w1)}\n"
                f"{city2}: {json.dumps(w2)}\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{\"city1\": \"{city1}\", '
                f'\"city2\": \"{city2}\", '
                f'\"warmer\": \"the warmer city name\", '
                f'\"more_humid\": \"the more humid city name\", '
                f'\"windier\": \"the windier city name\", '
                f'\"summary\": \"one sentence comparison\"}}'
            )
            return gl.nondet.exec_prompt(prompt)

        comparison                        = gl.eq_principle.prompt_comparative(
            analyze,
            "Both outputs compare the same two cities. "
            "They are equivalent if they identify the same warmer and windier city."
        )
        data[city1 + "_vs_" + city2]      = json.loads(comparison)
        self.store                        = json.dumps(data, sort_keys=True)

    # ── READ ───────────────────────────────────────────────────────

    @gl.public.view
    def read_weather(self, city: str) -> str:
        data = json.loads(self.store)
        if city in data:
            return json.dumps(data[city])
        return json.dumps({"error": city + " not cached. Call fetch_weather first."})

    @gl.public.view
    def read_all(self) -> str:
        return self.store

    @gl.public.view
    def list_locations(self) -> str:
        return json.dumps(list(LOCATIONS.keys()))

    @gl.public.view
    def hottest_city(self) -> str:
        data   = json.loads(self.store)
        cities = {k: v for k, v in data.items() if isinstance(v, dict) and "temperature" in v and v.get("status") == "ok"}
        if not cities:
            return json.dumps({"error": "No valid weather data cached yet."})
        hottest = max(cities.items(), key=lambda x: x[1]["temperature"])
        return json.dumps({"city": hottest[0], "data": hottest[1]})

    @gl.public.view
    def coldest_city(self) -> str:
        data   = json.loads(self.store)
        cities = {k: v for k, v in data.items() if isinstance(v, dict) and "temperature" in v and v.get("status") == "ok"}
        if not cities:
            return json.dumps({"error": "No valid weather data cached yet."})
        coldest = min(cities.items(), key=lambda x: x[1]["temperature"])
        return json.dumps({"city": coldest[0], "data": coldest[1]})

    @gl.public.view
    def humidity_alert(self, threshold: int) -> str:
        data   = json.loads(self.store)
        alerts = []
        for city, d in data.items():
            if isinstance(d, dict) and "humidity" in d and d.get("status") == "ok":
                if d["humidity"] >= threshold:
                    alerts.append({"city": city, "humidity": d["humidity"], "temperature": d.get("temperature")})
        if not alerts:
            return json.dumps({"message": "No cities above " + str(threshold) + "% humidity."})
        alerts.sort(key=lambda x: x["humidity"], reverse=True)
        return json.dumps({"threshold": threshold, "cities": alerts})

    @gl.public.view
    def wind_alert(self, threshold: int) -> str:
        data   = json.loads(self.store)
        alerts = []
        for city, d in data.items():
            if isinstance(d, dict) and "wind_speed" in d and d.get("status") == "ok":
                if d["wind_speed"] >= threshold:
                    alerts.append({"city": city, "wind_speed": d["wind_speed"], "temperature": d.get("temperature")})
        if not alerts:
            return json.dumps({"message": "No cities above " + str(threshold) + " km/h."})
        alerts.sort(key=lambda x: x["wind_speed"], reverse=True)
        return json.dumps({"threshold": threshold, "cities": alerts})

    @gl.public.view
    def freshness(self, city: str) -> str:
        hb = json.loads(self.pulse)
        if city not in hb:
            return json.dumps({"city": city, "fresh": False, "reason": city + " has never been fetched."})
        return json.dumps({"city": city, "fresh": True, "reason": city + " is in cache."})

    @gl.public.view
    def cache_report(self) -> str:
        hb   = json.loads(self.pulse)
        data = json.loads(self.store)
        cached, missing = [], []
        for city in LOCATIONS:
            if city in hb:
                d = data.get(city, {})
                cached.append({"city": city, "status": d.get("status", "unknown") if isinstance(d, dict) else "unknown"})
            else:
                missing.append({"city": city})
        return json.dumps({"total": len(LOCATIONS), "cached": len(cached), "missing": len(missing), "cached_cities": cached, "missing_cities": missing})
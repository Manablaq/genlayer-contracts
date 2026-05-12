# GenLayer Intelligent Contracts — Developer Best Practices

> A field guide for building production-ready Intelligent Contracts on GenLayer Studio.
> Based on real development of CryptoOracle, WeatherOracle, SocialOracle, and MultiKeyVault.
> GitHub: [Manablaq/genlayer-contracts](https://github.com/Manablaq/genlayer-contracts)

---

## Key Concepts

Before diving in, here's a plain-English summary of the GenLayer-specific terms used throughout this guide:

- **Intelligent Contract** — a smart contract that can fetch live data from the internet and use AI to process it, all on-chain
- **Validator** — a node on the GenLayer network that independently runs your contract's fetch logic to verify the result
- **Consensus** — multiple validators must agree on the result before it gets stored on-chain
- **`prompt_comparative`** — a built-in function that runs your fetch code across all validators and uses AI to decide if they all got the same answer
- **Equivalence string** — the rule you write to tell the AI what counts as "the same" result between two validators
- **GenLayer Studio** — the web-based IDE where you write, deploy, and test Intelligent Contracts

---

## Table of Contents

1. [Web Data Fetching](#1-web-data-fetching)
2. [State Management](#2-state-management)
3. [Equivalence Principles](#3-equivalence-principles)
4. [Contract Initialization](#4-contract-initialization)
5. [Error Handling](#5-error-handling)
6. [AI Prompts](#6-ai-prompts)
7. [Code Organization](#7-code-organization)
8. [API Compatibility](#8-api-compatibility)
9. [Studio-Specific Behavior](#9-studio-specific-behavior)
10. [Quick Reference](#10-quick-reference)
11. [Known Limitations](#11-known-limitations)

---

## 1. Web Data Fetching

### Always use `web.render()` — never `web.get()` with `response.body`

`web.get()` appears to work on Studio: it doesn't throw an error and the transaction finalizes. But `response.body` always returns an empty string. This is a silent failure.

**Incorrect:**
```python
@gl.public.write
def fetch_price(self, symbol: str) -> typing.Any:
    response = gl.nondet.web.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    self.store = response.body  # Always empty on Studio — no error thrown
```

**Correct** (from CryptoOracle):
```python
@gl.public.write
def fetch_price(self, symbol: str) -> typing.Any:
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"

    def fetch() -> str:
        try:
            raw = gl.nondet.web.render(url, mode="text")
            if not raw or raw.strip() == "null":
                return json.dumps({"error": "Binance API is down.", "status": "unavailable"})
            data  = json.loads(raw)
            price = float(data["lastPrice"])
            return json.dumps({
                "symbol": symbol,
                "price":  price,
                "status": "ok",
            }, sort_keys=True)
        except Exception:
            return json.dumps({"error": "Binance API is down.", "status": "unavailable"})

    fresh = gl.eq_principle.prompt_comparative(fetch, "...")
    all_data = json.loads(self.store)
    all_data[symbol] = json.loads(fresh)
    self.store = json.dumps(all_data, sort_keys=True)
```

### Multiple web requests inside one closure are fine

A single `prompt_comparative` closure can make multiple `web.render()` calls. SocialOracle fetches story IDs then fetches each story individually, all inside one closure:

```python
def _pull_stories(feed: str, limit: int = 10) -> str:
    ids_raw = gl.nondet.web.render(
        f"https://hacker-news.firebaseio.com/v0/{feed}stories.json",
        mode="text"
    )
    ids = json.loads(ids_raw)
    items = []
    for story_id in ids[:limit]:
        raw = gl.nondet.web.render(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
            mode="text"
        )
        s = json.loads(raw)
        items.append({"id": s.get("id"), "title": s.get("title"), "score": s.get("score", 0)})
    return json.dumps({"items": items, "status": "ok"}, sort_keys=True)
```

### Always handle errors inside the closure

Never let the closure raise an unhandled exception. Return a structured error JSON instead:

```python
def fetch() -> str:
    try:
        raw = gl.nondet.web.render(url, mode="text")
        if not raw or raw.strip() in ["null", "", "null\n"]:
            return json.dumps({"error": "API is down.", "status": "unavailable"})
        # ... parse and return data
    except Exception:
        return json.dumps({"error": "API is down.", "status": "unavailable"})
```

---

## 2. State Management

### Use `str` for all state fields — `TreeMap` does not persist on Studio

`TreeMap` works in local testing but state is lost after every transaction on GenLayer Studio. Use `str` fields with JSON serialization for all persistent state.

**Incorrect:**
```python
class CryptoOracle(gl.Contract):
    prices: TreeMap[str, str]  # State lost after each transaction on Studio
```

**Correct** (pattern used across all 4 contracts):
```python
class CryptoOracle(gl.Contract):
    store: str  # Persists correctly — holds all data as JSON string
    pulse: str  # Freshness / metadata tracking
```

### Always use `sort_keys=True` when serializing state

Validators independently execute your contract and must produce byte-identical output to reach consensus. Without `sort_keys=True`, Python dict key ordering is non-deterministic and consensus can fail on identical data.

```python
# Every state write in all 4 contracts uses sort_keys=True
self.store = json.dumps(all_data, sort_keys=True)
self.pulse = json.dumps(hb, sort_keys=True)
```

### Booleans and integers must be stored as strings

All state fields must be typed as `str`. Store booleans as `"true"` / `"false"` and integers as their string equivalents.

From MultiKeyVault:
```python
class MultiKeyVault(gl.Contract):
    is_paused:   str  # "true" or "false"
    rate_limit:  str  # "100"
    key_version: str  # "1", "2", "3", ...

def __init__(self, owner_address: str):
    self.is_paused   = "false"
    self.rate_limit  = "100"
    self.key_version = "1"

# Comparing boolean state
assert self.is_paused == "false", "Vault is already paused."

# Incrementing integer state
self.key_version = str(int(self.key_version) + 1)
```

### Initialize all state fields in `__init__`

```python
def __init__(self):
    self.store = "{}"   # Empty JSON object
    self.pulse = "{}"   # Or use a sentinel: self.pulse = "never"
```

Use `"{}"` for dict-like state. Use a sentinel string like `"never"` when you need to distinguish "never fetched" from "fetched but empty."

---

## 3. Equivalence Principles

### Calibrate your equivalence string to your data's volatility

The second argument to `prompt_comparative` defines what counts as "equivalent" results between validators. It is not boilerplate — it must reflect the actual characteristics of your data source.

**CryptoOracle** — prices fluctuate, allow 2% variance:
```python
gl.eq_principle.prompt_comparative(
    fetch,
    "The outputs represent the same crypto price. "
    "They are equivalent if both show an API error, "
    "or if price values are within 2% and symbol matches."
)
```

**WeatherOracle current** — sensor data, calibrated tolerances:
```python
gl.eq_principle.prompt_comparative(
    fetch,
    "The outputs represent weather data for the same city. "
    "They are equivalent if both show an API error, "
    "or if temperature is within 1 degree, humidity within 5%, "
    "and wind speed within 3 km/h of each other."
)
```

**WeatherOracle forecast** — less real-time, wider tolerance:
```python
gl.eq_principle.prompt_comparative(
    fetch,
    "The outputs represent a weather forecast for the same city. "
    "They are equivalent if both show an API error, "
    "or if temperatures are within 2 degrees and dates match exactly."
)
```

**SocialOracle trending** — stable feed, require 3 title matches:
```python
gl.eq_principle.prompt_comparative(
    fetch,
    "The outputs represent top stories from Hacker News. "
    "They are equivalent if both show an API error, "
    "or if they share at least 3 of the same story titles."
)
```

**SocialOracle latest** — volatile feed, allow looser match:
```python
gl.eq_principle.prompt_comparative(
    fetch,
    "The outputs represent new stories from Hacker News. "
    "They are equivalent if both show an API error, "
    "or if they share at least 2 of the same story titles or IDs."
)
```

**Rule:** Too strict → consensus fails on valid data. Too loose → bad data passes. Match your threshold to how much the data can legitimately differ between two validator calls made seconds apart.

---

## 4. Contract Initialization

### Pass caller address as a constructor parameter

`gl.message.sender_address` in `__init__` causes a runtime error at deploy time. Pass the owner address as a parameter instead.

**Incorrect:**
```python
def __init__(self):
    self.owner = gl.message.sender_address  # Runtime error on deploy
```

**Correct** (from MultiKeyVault):
```python
def __init__(self, owner_address: str):
    assert is_valid_address(owner_address), "Invalid owner address. Must start with 0x and be 42 characters long."
    self.owner           = owner_address
    self.allowed_callers = json.dumps([owner_address])
```

### Use `assert` for constructor validation — not `gl.vm.UserError`

`gl.vm.UserError` raised inside `__init__` causes deploy failure. Use `assert` for all constructor guards.

```python
# In __init__ — assert only
def __init__(self, owner_address: str):
    assert is_valid_address(owner_address), "Invalid owner address."
    assert len(owner_address) == 42, "Address must be 42 characters."

# In write methods — both assert and gl.vm.UserError work
@gl.public.write
def fetch_price(self, symbol: str) -> typing.Any:
    if symbol not in SUPPORTED:
        raise gl.vm.UserError(symbol + " is not supported.")
```

---

## 5. Error Handling

### Return structured error JSON — don't raise inside the closure

Write methods that use `prompt_comparative` should handle errors inside the closure and return a structured error object, not raise an exception.

```python
def fetch() -> str:
    try:
        raw = gl.nondet.web.render(url, mode="text")
        if not raw or raw.strip() == "null":
            return json.dumps({"error": "API is down.", "status": "unavailable"})
        data = json.loads(raw)
        return json.dumps({"data": data, "status": "ok"}, sort_keys=True)
    except Exception:
        return json.dumps({"error": "API is down.", "status": "unavailable"})
```

### Check for error status when reading cached data

```python
@gl.public.view
def read_price(self, symbol: str) -> str:
    all_data = json.loads(self.store)
    if symbol in all_data:
        return json.dumps(all_data[symbol])
    return json.dumps({"error": symbol + " not cached. Call fetch_price first."})
```

### Use `gl.vm.UserError` for precondition failures in write methods

When a write method requires cached data that doesn't exist yet:

```python
@gl.public.write
def generate_briefing(self) -> typing.Any:
    data = json.loads(self.store)
    if "trending" not in data:
        raise gl.vm.UserError("No stories cached. Call fetch_trending first.")
```

---

## 6. AI Prompts

### Always define an exact JSON response schema in the prompt

Free-form AI responses are hard to parse and hard to write equivalence checks for. Tell the model exactly what JSON to return.

From WeatherOracle:
```python
def analyze() -> str:
    prompt = (
        f"Analyze this weather data for {city} and determine if conditions are dangerous:\n\n"
        f"{json.dumps(weather)}\n\n"
        f"Consider: temperature extremes, high winds above 60 km/h, "
        f"heavy rain above 10mm, severe weathercodes (95-99).\n\n"
        f"Respond ONLY with JSON:\n"
        f'{{\"alert_level\": \"safe\" or \"caution\" or \"danger\", '
        f'\"reason\": \"one sentence explanation\", '
        f'\"recommendation\": \"one sentence advice\"}}'
    )
    return gl.nondet.exec_prompt(prompt)
```

### Write equivalence checks that target key decisions, not exact wording

```python
alert = gl.eq_principle.prompt_comparative(
    analyze,
    # Only check the decision field — wording of reason/recommendation can vary
    "Both outputs assess the same weather conditions. "
    "They are equivalent if they assign the same alert level."
)
data[city]["alert"] = json.loads(alert)
```

---

## 7. Code Organization

### Be careful with closures defined inside loops

When defining a `fetch` closure inside a `for` loop, the closure captures the *variable*, not its *value* at the time of definition. This is a standard Python closure-in-loop bug.

CryptoOracle's `fetch_prices` and WeatherOracle's `fetch_multiple` both use this pattern and worked correctly in Studio — because `prompt_comparative` was called immediately within the same iteration. But this is not guaranteed behavior.

**Risky:**
```python
for symbol in symbols:
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    def fetch() -> str:
        return gl.nondet.web.render(url, mode="text")  # Captures variable, not value
    fresh = gl.eq_principle.prompt_comparative(fetch, "...")
```

**Safe — use default argument binding:**
```python
for symbol in symbols:
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    def fetch(u=url) -> str:  # Captures value at definition time
        return gl.nondet.web.render(u, mode="text")
    fresh = gl.eq_principle.prompt_comparative(fetch, "...")
```



If multiple write methods share the same fetch logic, extract it into a module-level function (outside the class). GenLayer supports calling module-level functions from inside closures.

```python
# Module-level — defined outside the class
def _pull_current(city: str, lat: str, lon: str) -> str:
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,..."
        raw = gl.nondet.web.render(url, mode="text")
        # ... parse and return
    except Exception:
        return json.dumps({"error": "Open-Meteo API is down.", "status": "unavailable"})

class WeatherOracle(gl.Contract):
    @gl.public.write
    def fetch_weather(self, city: str) -> typing.Any:
        lat, lon = LOCATIONS[city]
        def fetch() -> str:
            return _pull_current(city, lat, lon)  # Calls module-level function
        fresh = gl.eq_principle.prompt_comparative(fetch, "...")
```

### Use private helper methods for repeated contract logic

```python
class MultiKeyVault(gl.Contract):
    def _is_owner(self, address: str) -> bool:
        return address == self.owner

    def _log_call(self, action: str, detail: str) -> None:
        log = json.loads(self.audit_log)
        log.append({"action": action, "detail": detail})
        if len(log) > 50:
            log = log[-50:]  # Cap log size to manage state growth
        self.audit_log = json.dumps(log)
```

---

## 8. API Compatibility

### Only use public APIs

GenLayer consensus requires all validators to independently fetch the same data. If your API requires authentication (OAuth, API keys in headers, HMAC signing), validators cannot replicate the call.

**Compatible:**
```
Binance public ticker:    https://api.binance.com/api/v3/ticker/24hr
Open-Meteo:               https://api.open-meteo.com/v1/forecast
Hacker News Firebase:     https://hacker-news.firebaseio.com/v0/
CoinGecko public:         https://api.coingecko.com/api/v3/
```

**Incompatible:**
```
Any API requiring Authorization headers
Any API requiring OAuth tokens
Any API requiring HMAC request signing
Any API behind a login or session wall
```

**Note on private keys:** MultiKeyVault stores API keys on-chain and appends them directly to the URL at fetch time (`web.render(url + secret, mode="text")`). This works only for APIs that accept the key as a URL parameter — not for APIs requiring it in headers.

---

## 9. Studio-Specific Behavior

### Testing order matters

For contracts where read methods depend on write methods having run first:

1. Deploy the contract
2. Call the write method (e.g. `fetch_price`)
3. Wait for the transaction to finalize (30–90 seconds)
4. Call the read method (e.g. `read_price`)

Calling a read method before the corresponding write method has finalized will return the empty-state default.

### Empty methods panel = schema error

If the methods panel is empty after deploying, your contract has a schema error — usually a type annotation issue. Re-check all method signatures and state field declarations.

### Leader rotation is expected

You may see more than 5 validators appearing in transaction logs. This is normal — it reflects cumulative leaders across multiple consensus rounds, not the validator set size.

---

## 10. Quick Reference

| Situation | Use This | Not This |
|---|---|---|
| Fetch web data | `web.render(mode="text")` | `web.get()` + `response.body` |
| Persistent state | `str` fields + `json.dumps` | `TreeMap` |
| JSON serialization | `json.dumps(..., sort_keys=True)` | `json.dumps()` without sort |
| Web + AI consensus | `prompt_comparative` | `run_nondet_unsafe` |
| Booleans in state | `"true"` / `"false"` strings | `bool` type |
| Integers in state | `str(int)` — `"100"`, `"1"` | `int` type |
| Get caller address | Constructor parameter | `gl.message.sender_address` in `__init__` |
| Validate in constructor | `assert` | `gl.vm.UserError` |
| Validate in write methods | `gl.vm.UserError` or `assert` | — |
| Shared fetch logic | Module-level function | Duplicated closures |
| AI output | Specific JSON schema in prompt | Free-form text |
| Closures in loops | Default argument binding (`u=url`) | Bare variable capture |

---

## 11. Known Limitations

Confirmed platform limitations as of the time of writing. These are not bugs in your contract.

| Limitation | Impact | Workaround |
|---|---|---|
| `web.get()` + `response.body` returns empty | Silent data loss | Use `web.render()` |
| `TreeMap` state does not persist on Studio | State lost after each transaction | Use `str` + JSON serialization |
| `run_nondet_unsafe` fails with web fetching | Cannot combine unsafe nondeterminism with web calls | Use `prompt_comparative` |
| Private APIs incompatible with consensus | Validators cannot independently replicate auth-required calls | Use public APIs only |
| `gl.message.sender_address` in `__init__` causes deploy failure | Contract fails to deploy | Pass caller address as constructor parameter |
| Leader rotation shows more than 5 validators | Looks alarming in logs | Normal behavior — not a bug |

---

## Contract Examples

| Contract | Key Patterns | Source |
|---|---|---|
| CryptoOracle | `web.render()`, calibrated price equivalence (2%), `str` state | [/crypto-oracle](https://github.com/Manablaq/genlayer-contracts/tree/main/crypto-oracle) |
| WeatherOracle | Module-level fetch helper, per-method equivalence thresholds, AI alerts | [/weather-oracle](https://github.com/Manablaq/genlayer-contracts/tree/main/weather-oracle) |
| SocialOracle | Multiple web calls per closure, volatility-calibrated equivalence, AI briefings | [/social-oracle](https://github.com/Manablaq/genlayer-contracts/tree/main/social-oracle) |
| MultiKeyVault | Boolean/int as string, `assert` in `__init__`, audit log, rate limiting | [/multi-key-vault](https://github.com/Manablaq/genlayer-contracts/tree/main/multi-key-vault) |

---

*Authored by [Manablaq](https://github.com/Manablaq) — GenLayer Builder Program, Tools & Infrastructure track.*

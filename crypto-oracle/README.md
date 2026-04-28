# CryptoOracle

> Live cryptocurrency price intelligence on GenLayer — fetched, verified by consensus, and cached on-chain.

---

## Overview

CryptoOracle is a GenLayer Intelligent Contract that tracks real-time prices for 10 major cryptocurrencies using the Binance public API. What makes it different from a traditional price feed is how the data gets on-chain: five independent validators each fetch from Binance simultaneously and must agree on the result within a 2% tolerance before anything is written to state. No single point of trust. No data provider with special privileges.

Once prices are cached, all read methods are completely free — no gas, no consensus, instant response.

---

## Supported Assets

| Symbol | Name | Exchange |
|---|---|---|
| BTCUSDT | Bitcoin | Binance |
| ETHUSDT | Ethereum | Binance |
| SOLUSDT | Solana | Binance |
| BNBUSDT | BNB | Binance |
| XRPUSDT | XRP | Binance |
| ADAUSDT | Cardano | Binance |
| DOGEUSDT | Dogecoin | Binance |
| LINKUSDT | Chainlink | Binance |
| MATICUSDT | Polygon | Binance |
| AVAXUSDT | Avalanche | Binance |

---

## Methods

### Write Methods
These methods fetch live data and write to chain. They require gas and go through validator consensus.

| Method | Parameters | Description |
|---|---|---|
| `fetch_price` | `symbol: str` | Fetch and cache a single asset |
| `fetch_prices` | `symbols: list` | Fetch and cache multiple assets in one transaction |
| `generate_summary` | — | AI two-sentence market briefing from all cached prices |
| `calculate_portfolio` | `holdings: str` | Calculate total USD value of a portfolio |

### Read Methods
These methods read from the on-chain cache. No gas required.

| Method | Parameters | Description |
|---|---|---|
| `read_all` | — | All cached prices and summaries |
| `read_price` | `symbol: str` | One cached price |
| `read_asset_info` | `symbol: str` | Asset metadata |
| `list_assets` | — | All supported symbols |
| `top_mover` | — | Asset with the largest 24h price change |
| `movers` | `direction: str` | All assets moving "up" or "down" |
| `liquidity` | `symbol: str` | Volume-based liquidity assessment |
| `freshness` | `symbol: str` | Whether a symbol has ever been fetched |
| `cache_report` | — | Full cache status across all assets |

---

## Deploying

1. Open [studio.genlayer.com](https://studio.genlayer.com)
2. Paste `contract.py` into the editor
3. Click **Deploy new instance** — no parameters needed
4. Wait for FINALIZED

---

## Testing

```
# Fetch one price
fetch_price("BTCUSDT")

# Fetch several at once
fetch_prices(["BTCUSDT", "ETHUSDT", "SOLUSDT"])

# Generate AI market summary (needs cached prices first)
generate_summary()

# Calculate portfolio value
calculate_portfolio('{"BTCUSDT": 0.5, "ETHUSDT": 2.0}')

# Read results (free)
read_all()
read_price("BTCUSDT")
top_mover()
liquidity("BTCUSDT")
```

---

## How Consensus Works

Each `fetch_price` call runs through `prompt_comparative` with a 2% tolerance. Crypto prices change every millisecond — five validators fetching at slightly different moments will get slightly different numbers. The tolerance allows them to agree on results that are close enough while still rejecting outliers caused by API errors or data corruption.

`generate_summary` also uses `prompt_comparative` — two validators may phrase a market briefing differently while conveying the same meaning. The LLM-based equivalence check handles subjective text correctly.

---

## State

| Variable | Type | Purpose |
|---|---|---|
| `store` | `str` | JSON cache of all price data |
| `pulse` | `str` | Tracks which assets have been fetched |
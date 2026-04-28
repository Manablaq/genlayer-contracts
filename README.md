# GenLayer Intelligent Contracts

Traditional smart contracts are deterministic by design — they can only work with data that already exists on-chain. They cannot browse the internet, call an API, or reason about the results. That constraint has defined the limits of what blockchain applications can do for over a decade.

GenLayer changes that. Intelligent Contracts are written in Python and can fetch live data from any public API, run AI prompts natively, and reach consensus across validators — all without external middleware or trusted intermediaries. The contract itself becomes the oracle.

This repository contains four Intelligent Contracts built to explore what that capability makes possible: a real-time crypto price feed, a global weather monitor, a social media intelligence layer, and a secure multi-key API vault. Each one fetches live data, processes it through five-validator consensus, caches it on-chain, and makes it available for free through read methods.

---

## Contracts

### 1. CryptoOracle
**Folder:** `crypto-oracle/`

Tracks real-time prices for 10 major cryptocurrencies using the Binance public API. Five validators independently verify each price fetch before caching on-chain. Includes AI-generated market briefings, portfolio value calculation, liquidity assessment, and biggest mover detection.

**Assets:** Bitcoin · Ethereum · Solana · BNB · XRP · Cardano · Dogecoin · Chainlink · Polygon · Avalanche

**Methods:** 4 write · 9 read · **13 total**

---

### 2. WeatherOracle
**Folder:** `weather-oracle/`

Fetches live weather conditions for 13 cities worldwide from the Open-Meteo API. Goes beyond raw data with AI-powered danger alerts, city-vs-city comparisons, global briefings, and threshold monitoring for humidity and wind. No API key required.

**Cities:** London · New York · Lagos · Tokyo · Paris · Dubai · Singapore · Nairobi · Port Harcourt · Abuja · Berlin · Sydney · Toronto

**Methods:** 6 write · 9 read · **15 total**

---

### 3. SocialOracle
**Folder:** `social-oracle/`

Brings Hacker News on-chain — monitoring top, new, and best-rated story feeds through validator consensus. Uses GenLayer's native LLM to generate tech trend briefings and topic-specific analysis from cached stories. Includes keyword search and story leaderboards. No API key required.

**Feeds:** Top Stories · New Stories · Best Stories

**Methods:** 5 write · 7 read · **12 total**

---

### 4. MultiKeyVault
**Folder:** `multi-key-vault/`

A secure API key manager that stores multiple named secrets on-chain and makes authenticated API calls without exposing them. Each key has its own usage counter. Includes emergency wipe, whitelist access control, and a full on-chain audit log.

**Methods:** 13 write · 11 read · **24 total**

---

## Totals

| | Count |
|---|---|
| Contracts | 4 |
| Total methods | 64 |
| APIs used | Binance · Open-Meteo · Hacker News Firebase |
| Network | GenLayer Studio (studionet) |

---

## How It Works

All contracts follow the same pattern:

```
External API → web.render() → prompt_comparative → on-chain cache → free reads
```

Five validators independently fetch the same data and must agree before anything is written to chain. AI methods use `exec_prompt` natively inside the contract — no external AI service needed.

---

## Deployment Status

| Contract | Status |
|---|---|
| CryptoOracle | ✅ Deployed and tested |
| WeatherOracle | ✅ Deployed and tested |
| SocialOracle | ✅ Deployed and tested |
| MultiKeyVault | ✅ Deployed and tested |

To deploy: paste any contract into [studio.genlayer.com](https://studio.genlayer.com) and click **Deploy new instance**. MultiKeyVault requires `owner_address` as a constructor parameter. All others deploy with no parameters.

---

## Repository Structure

```
genlayer-contracts/
├── crypto-oracle/
│   ├── contract.py
│   └── README.md
├── weather-oracle/
│   ├── contract.py
│   └── README.md
├── social-oracle/
│   ├── contract.py
│   └── README.md
├── multi-key-vault/
│   ├── contract.py
│   └── README.md
├── ux-improvements/
│   └── UX_IMPROVEMENTS.md
└── README.md
```

---
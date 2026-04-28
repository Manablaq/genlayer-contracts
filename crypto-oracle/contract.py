# { "Depends": "py-genlayer:test" }

from genlayer import *
import json
import typing

SUPPORTED = {
    "BTCUSDT":   {"name": "Bitcoin",   "abbr": "BTC",   "category": "crypto", "exchange": "Binance"},
    "ETHUSDT":   {"name": "Ethereum",  "abbr": "ETH",   "category": "crypto", "exchange": "Binance"},
    "SOLUSDT":   {"name": "Solana",    "abbr": "SOL",   "category": "crypto", "exchange": "Binance"},
    "BNBUSDT":   {"name": "BNB",       "abbr": "BNB",   "category": "crypto", "exchange": "Binance"},
    "XRPUSDT":   {"name": "XRP",       "abbr": "XRP",   "category": "crypto", "exchange": "Binance"},
    "ADAUSDT":   {"name": "Cardano",   "abbr": "ADA",   "category": "crypto", "exchange": "Binance"},
    "DOGEUSDT":  {"name": "Dogecoin",  "abbr": "DOGE",  "category": "crypto", "exchange": "Binance"},
    "LINKUSDT":  {"name": "Chainlink", "abbr": "LINK",  "category": "crypto", "exchange": "Binance"},
    "MATICUSDT": {"name": "Polygon",   "abbr": "MATIC", "category": "crypto", "exchange": "Binance"},
    "AVAXUSDT":  {"name": "Avalanche", "abbr": "AVAX",  "category": "crypto", "exchange": "Binance"},
}


class CryptoOracle(gl.Contract):

    store: str
    pulse: str

    def __init__(self):
        self.store = "{}"
        self.pulse = "{}"

    # ── FETCH ───────────────────────────────────────────────────────

    @gl.public.write
    def fetch_price(self, symbol: str) -> typing.Any:
        if symbol not in SUPPORTED:
            raise gl.vm.UserError(symbol + " is not supported.")
        url  = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        info = SUPPORTED[symbol]

        def fetch() -> str:
            try:
                raw = gl.nondet.web.render(url, mode="text")
                if not raw or raw.strip() == "null":
                    return json.dumps({"error": "Binance API is down.", "status": "unavailable"})
                data   = json.loads(raw)
                price  = float(data["lastPrice"])
                change = float(data["priceChangePercent"])
                return json.dumps({
                    "symbol":        symbol,
                    "name":          info["name"],
                    "abbr":          info["abbr"],
                    "price":         price,
                    "display_price": "$" + str(round(price, 2)),
                    "change_pct":    round(change, 2),
                    "change_dir":    "up" if change >= 0 else "down",
                    "high_24h":      float(data["highPrice"]),
                    "low_24h":       float(data["lowPrice"]),
                    "open_24h":      float(data["openPrice"]),
                    "volume":        float(data["volume"]),
                    "volume_usdt":   float(data["quoteVolume"]),
                    "exchange":      info["exchange"],
                    "status":        "ok",
                }, sort_keys=True)
            except Exception:
                return json.dumps({"error": "Binance API is down.", "status": "unavailable"})

        fresh        = gl.eq_principle.prompt_comparative(fetch, "The outputs represent the same crypto price. They are equivalent if both show an API error, or if price values are within 2% and symbol matches.")
        all_data     = json.loads(self.store)
        all_data[symbol] = json.loads(fresh)
        self.store   = json.dumps(all_data, sort_keys=True)
        hb           = json.loads(self.pulse)
        hb[symbol]   = "updated"
        self.pulse   = json.dumps(hb, sort_keys=True)

    @gl.public.write
    def fetch_prices(self, symbols: list) -> typing.Any:
        all_data = json.loads(self.store)
        hb       = json.loads(self.pulse)
        for symbol in symbols:
            if symbol not in SUPPORTED:
                raise gl.vm.UserError(symbol + " is not supported.")
            url  = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            info = SUPPORTED[symbol]
            def fetch() -> str:
                try:
                    raw = gl.nondet.web.render(url, mode="text")
                    if not raw or raw.strip() == "null":
                        return json.dumps({"error": "Binance API is down.", "status": "unavailable"})
                    data   = json.loads(raw)
                    price  = float(data["lastPrice"])
                    change = float(data["priceChangePercent"])
                    return json.dumps({
                        "symbol":        symbol,
                        "name":          info["name"],
                        "abbr":          info["abbr"],
                        "price":         price,
                        "display_price": "$" + str(round(price, 2)),
                        "change_pct":    round(change, 2),
                        "change_dir":    "up" if change >= 0 else "down",
                        "high_24h":      float(data["highPrice"]),
                        "low_24h":       float(data["lowPrice"]),
                        "open_24h":      float(data["openPrice"]),
                        "volume":        float(data["volume"]),
                        "volume_usdt":   float(data["quoteVolume"]),
                        "exchange":      info["exchange"],
                        "status":        "ok",
                    }, sort_keys=True)
                except Exception:
                    return json.dumps({"error": "Binance API is down.", "status": "unavailable"})
            fresh            = gl.eq_principle.prompt_comparative(fetch, "The outputs represent the same crypto price. They are equivalent if both show an API error, or if price values are within 2%.")
            all_data[symbol] = json.loads(fresh)
            hb[symbol]       = "updated"
        self.store = json.dumps(all_data, sort_keys=True)
        self.pulse = json.dumps(hb, sort_keys=True)

    # ── AI ─────────────────────────────────────────────────────────

    @gl.public.write
    def generate_summary(self) -> typing.Any:
        all_data = json.loads(self.store)
        if not all_data:
            return
        def summarize() -> str:
            prompt = (
                f"You are a professional financial analyst. Based on this crypto market data, "
                f"write a concise two-sentence briefing covering current trends:\n\n"
                f"{json.dumps(all_data)}\n\n"
                f"Respond with only the briefing, nothing else."
            )
            return gl.nondet.exec_prompt(prompt)
        summary              = gl.eq_principle.prompt_comparative(summarize, "Both outputs summarize the same market. They are equivalent if they describe the same trend direction.")
        all_data["summary"]  = summary
        self.store           = json.dumps(all_data, sort_keys=True)

    @gl.public.write
    def calculate_portfolio(self, holdings: str) -> typing.Any:
        all_data    = json.loads(self.store)
        portfolio   = json.loads(holdings)
        total_value = 0.0
        breakdown   = []
        for symbol, amount in portfolio.items():
            if symbol not in all_data:
                breakdown.append({"symbol": symbol, "error": "Price not cached."})
                continue
            p = all_data[symbol]
            if not isinstance(p, dict) or p.get("status") != "ok":
                breakdown.append({"symbol": symbol, "error": "Price unavailable."})
                continue
            price       = p["price"]
            value       = price * amount
            total_value = total_value + value
            breakdown.append({
                "symbol":        symbol,
                "name":          p.get("name", symbol),
                "abbr":          p.get("abbr", symbol),
                "amount":        amount,
                "price":         price,
                "display_price": p.get("display_price", ""),
                "value_usd":     round(value, 2),
                "display_value": "$" + str(round(value, 2)),
            })
        result               = {"total_usd": round(total_value, 2), "display_total": "$" + str(round(total_value, 2)), "breakdown": breakdown}
        all_data["portfolio"] = result
        self.store            = json.dumps(all_data, sort_keys=True)

    # ── READ ───────────────────────────────────────────────────────

    @gl.public.view
    def read_all(self) -> str:
        return self.store

    @gl.public.view
    def read_price(self, symbol: str) -> str:
        all_data = json.loads(self.store)
        if symbol in all_data:
            return json.dumps(all_data[symbol])
        return json.dumps({"error": symbol + " not cached. Call fetch_price first."})

    @gl.public.view
    def read_asset_info(self, symbol: str) -> str:
        info = SUPPORTED.get(symbol)
        if not info:
            return json.dumps({"error": symbol + " not found."})
        return json.dumps({"symbol": symbol, "name": info["name"], "abbr": info["abbr"], "exchange": info["exchange"]})

    @gl.public.view
    def list_assets(self) -> str:
        assets = []
        for sym, info in SUPPORTED.items():
            assets.append({"symbol": sym, "name": info["name"], "abbr": info["abbr"], "exchange": info["exchange"]})
        return json.dumps(assets)

    @gl.public.view
    def top_mover(self) -> str:
        all_data    = json.loads(self.store)
        best_symbol = ""
        best_change = 0.0
        for sym, d in all_data.items():
            if not isinstance(d, dict): continue
            if d.get("status") != "ok": continue
            if "change_pct" not in d: continue
            chg = abs(d["change_pct"])
            if chg > best_change:
                best_change = chg
                best_symbol = sym
        if not best_symbol:
            return json.dumps({"error": "No data cached yet."})
        w = all_data[best_symbol]
        return json.dumps({"symbol": best_symbol, "change_pct": w["change_pct"], "change_dir": w["change_dir"], "display_price": w.get("display_price",""), "name": w.get("name",""), "abbr": w.get("abbr","")})

    @gl.public.view
    def movers(self, direction: str) -> str:
        if direction not in ["up", "down"]:
            return json.dumps({"error": "Direction must be 'up' or 'down'."})
        all_data = json.loads(self.store)
        result   = {}
        for sym, d in all_data.items():
            if not isinstance(d, dict): continue
            if d.get("status") != "ok": continue
            if d.get("change_dir") == direction:
                result[sym] = {"symbol": sym, "name": d.get("name",sym), "abbr": d.get("abbr",sym), "display_price": d.get("display_price",""), "change_pct": d.get("change_pct",0), "change_dir": d.get("change_dir","")}
        if not result:
            return json.dumps({"message": "No assets moving " + direction + "."})
        return json.dumps(result)

    @gl.public.view
    def liquidity(self, symbol: str) -> str:
        all_data = json.loads(self.store)
        if symbol not in all_data:
            return json.dumps({"error": symbol + " not cached."})
        d = all_data[symbol]
        if not isinstance(d, dict) or d.get("status") != "ok":
            return json.dumps({"error": "Price data unavailable."})
        if "volume_usdt" not in d:
            return json.dumps({"error": "No volume data for " + symbol + "."})
        volume = d["volume_usdt"]
        if volume >= 100000000:   level, message = "very_high", "Excellent liquidity. Suitable for large trades."
        elif volume >= 10000000:  level, message = "high",      "Good liquidity. Suitable for most trades."
        elif volume >= 1000000:   level, message = "medium",    "Moderate liquidity. Use limit orders for large trades."
        else:                     level, message = "low",       "Low liquidity. Exercise caution with large trades."
        return json.dumps({"symbol": symbol, "volume_usdt": volume, "display_volume": "$" + str(round(volume,0)), "liquidity": level, "message": message})

    @gl.public.view
    def freshness(self, symbol: str) -> str:
        hb = json.loads(self.pulse)
        if symbol not in hb:
            return json.dumps({"symbol": symbol, "fresh": False, "reason": symbol + " has never been fetched."})
        return json.dumps({"symbol": symbol, "fresh": True, "reason": symbol + " is in cache."})

    @gl.public.view
    def cache_report(self) -> str:
        hb       = json.loads(self.pulse)
        all_data = json.loads(self.store)
        cached, missing = [], []
        for sym, info in SUPPORTED.items():
            entry = {"symbol": sym, "name": info["name"], "abbr": info["abbr"]}
            if sym in hb:
                d = all_data.get(sym, {})
                entry["status"] = d.get("status", "unknown") if isinstance(d, dict) else "unknown"
                cached.append(entry)
            else:
                missing.append(entry)
        return json.dumps({"total": len(SUPPORTED), "cached": len(cached), "missing": len(missing), "cached_assets": cached, "missing_assets": missing})
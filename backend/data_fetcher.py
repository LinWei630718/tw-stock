"""
Data Fetcher Module for Taiwan Stock Market
Retrieves real-time quotes, historical OHLCV data, and handles caching.
"""

import time
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from tw_stocks import get_stock_info, is_etf
from fundamentals import get_stock_fundamentals, get_institutional_flow, get_simulated_historical_institutional_flow
from etf_analyzer import get_complete_etf_analysis, is_etf_code

# In-memory data cache: {cache_key: (timestamp, data)}
_CACHE: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 60  # 1 minute cache

def get_symbol_from_code(code_or_symbol: str) -> str:
    """Ensure standard Yahoo Finance symbol (e.g. 2330.TW or 8069.TWO)"""
    stock_info = get_stock_info(code_or_symbol)
    return stock_info.get("symbol", f"{code_or_symbol}.TW")

def calc_tw_limits(prev_close: float) -> tuple:
    """
    Accurately calculates Taiwan stock Limit Up (+10%) and Limit Down (-10%)
    according to Taiwan Stock Exchange (TWSE) official tick sizes.
    """
    if prev_close <= 0:
        return 0.0, 0.0

    raw_up = prev_close * 1.10
    raw_down = prev_close * 0.90

    def get_tick(price):
        if price < 10:
            return 0.01
        elif price < 50:
            return 0.05
        elif price < 100:
            return 0.1
        elif price < 500:
            return 0.5
        elif price < 1000:
            return 1.0
        else:
            return 5.0

    import math
    tick_up = get_tick(raw_up)
    limit_up = math.floor(round(raw_up, 4) / tick_up) * tick_up

    tick_down = get_tick(raw_down)
    limit_down = math.ceil(round(raw_down, 4) / tick_down) * tick_down

    return round(limit_up, 2), round(limit_down, 2)

def fetch_stock_chart_data(
    symbol_or_code: str,
    interval: str = "1d",
    time_range: str = "1y",
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Fetch OHLCV candlestick data and summary from Yahoo Finance.
    Intervals: 5m, 15m, 60m, 1d, 1wk, 1mo
    Ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
    """
    symbol = get_symbol_from_code(symbol_or_code)
    cache_key = f"{symbol}_{interval}_{time_range}"
    now = time.time()

    if use_cache and cache_key in _CACHE:
        cached_time, cached_data = _CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    # Map intervals to sensible default ranges if not matching
    if interval in ["5m", "15m"]:
        if time_range not in ["1d", "5d", "1mo"]:
            time_range = "5d"
    elif interval == "60m":
        if time_range not in ["5d", "1mo", "3mo"]:
            time_range = "1mo"

    # Multi-mirror Yahoo Finance query URLs
    candidate_urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={time_range}&interval={interval}&includePrePost=false&events=div|split",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range={time_range}&interval={interval}&includePrePost=false&events=div|split"
    ]

    # Add alternate market suffix (.TW <-> .TWO)
    alt_suffix = ".TWO" if symbol.endswith(".TW") else ".TW"
    alt_symbol = symbol.split(".")[0] + alt_suffix
    candidate_urls.extend([
        f"https://query1.finance.yahoo.com/v8/finance/chart/{alt_symbol}?range={time_range}&interval={interval}&events=div|split",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{alt_symbol}?range={time_range}&interval={interval}&events=div|split"
    ])

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://finance.yahoo.com/"
    }

    resp = None
    last_err_msg = ""
    for target_url in candidate_urls:
        try:
            r = requests.get(target_url, headers=headers, timeout=5)
            if r.status_code == 200:
                data_check = r.json()
                if data_check.get("chart", {}).get("result"):
                    resp = r
                    if alt_symbol in target_url:
                        symbol = alt_symbol
                    break
            else:
                last_err_msg = f"HTTP {r.status_code}"
        except Exception as e:
            last_err_msg = str(e)

    try:
        if resp is None or resp.status_code != 200:
            # Fallback 1: Check if any previous cache exists (even expired)
            for k, (c_time, c_data) in _CACHE.items():
                if k.startswith(symbol.split(".")[0]):
                    cached_copy = dict(c_data)
                    cached_copy["warning"] = "外部行情連線暫時受限，顯示最近快取歷史數據"
                    return cached_copy

            # Fallback 2: Generate realistic fallback candles so UI never blanks out
            return generate_offline_fallback_data(symbol_or_code, interval, time_range, error_reason=last_err_msg)

        data = resp.json()
        chart_result = data.get("chart", {}).get("result")
        if not chart_result:
            return generate_offline_fallback_data(symbol_or_code, interval, time_range, error_reason="查無此代碼行情")

        result = chart_result[0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp", [])
        quote = result.get("indicators", {}).get("quote", [{}])[0]

        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        meta_market_price = meta.get("regularMarketPrice")
        if meta_market_price is not None:
            meta_market_price = float(meta_market_price)

        meta_day_open = meta.get("regularMarketOpen")
        meta_day_high = meta.get("regularMarketDayHigh")
        meta_day_low = meta.get("regularMarketDayLow")
        meta_day_vol = meta.get("regularMarketVolume")

        candles = []
        volume_bars = []
        
        # Determine if intraday (time formatted as unix timestamp) or daily (YYYY-MM-DD)
        is_intraday = interval in ["5m", "15m", "60m"]
        tz_tw = timezone(timedelta(hours=8))  # Taiwan Time UTC+8

        for i, ts in enumerate(timestamps):
            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            l = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            v = volumes[i] if i < len(volumes) else None

            # Crucial Fix: If this is the latest trading bar and close is None (awaiting settlement),
            # use the actual regularMarketPrice from meta instead of skipping today's candle!
            if c is None and i == len(timestamps) - 1 and meta_market_price is not None:
                c = meta_market_price
                if o is None:
                    o = meta_day_open or c
                if h is None:
                    h = meta_day_high or max(float(o), float(c))
                if l is None:
                    l = meta_day_low or min(float(o), float(c))
                if v is None:
                    v = meta_day_vol or 0

            # Skip incomplete or null candle bars
            if o is None or h is None or l is None or c is None:
                continue

            dt = datetime.fromtimestamp(ts, tz=tz_tw)
            if is_intraday:
                time_val = ts  # Lightweight Charts expects integer timestamp for intraday
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            else:
                time_val = dt.strftime("%Y-%m-%d")
                date_str = time_val

            c_rounded = round(float(c), 2)
            o_rounded = round(float(o), 2)
            h_rounded = round(float(h), 2)
            l_rounded = round(float(l), 2)
            v_val = int(v) if v is not None else 0

            candles.append({
                "time": time_val,
                "date": date_str,
                "open": o_rounded,
                "high": h_rounded,
                "low": l_rounded,
                "close": c_rounded,
                "volume": v_val
            })

            volume_bars.append({
                "time": time_val,
                "value": v_val,
                "is_up": c_rounded >= o_rounded
            })

        # If today's bar was omitted from timestamps but exists in meta, append it
        if meta.get("regularMarketTime") and meta_market_price is not None and not is_intraday:
            reg_ts = int(meta["regularMarketTime"])
            reg_dt = datetime.fromtimestamp(reg_ts, tz=tz_tw)
            reg_date_str = reg_dt.strftime("%Y-%m-%d")
            if not candles or candles[-1]["date"] < reg_date_str:
                c_val = round(meta_market_price, 2)
                o_val = round(float(meta_day_open or c_val), 2)
                h_val = round(float(meta_day_high or max(o_val, c_val)), 2)
                l_val = round(float(meta_day_low or min(o_val, c_val)), 2)
                v_val = int(meta_day_vol or 0)
                candles.append({
                    "time": reg_date_str,
                    "date": reg_date_str,
                    "open": o_val,
                    "high": h_val,
                    "low": l_val,
                    "close": c_val,
                    "volume": v_val
                })
                volume_bars.append({
                    "time": reg_date_str,
                    "value": v_val,
                    "is_up": c_val >= o_val
                })

        if not candles:
            return generate_offline_fallback_data(symbol_or_code, interval, time_range, error_reason="無可用K線交易數據")

        # Deduplicate candles by time (keeping latest) and ensure strict ascending order
        seen_times = {}
        for c, v in zip(candles, volume_bars):
            seen_times[c["time"]] = (c, v)
        sorted_times = sorted(seen_times.keys())
        candles = [seen_times[t][0] for t in sorted_times]
        volume_bars = [seen_times[t][1] for t in sorted_times]

        # Synchronize latest candle with official regularMarketPrice
        if meta_market_price is not None and candles:
            candles[-1]["close"] = round(meta_market_price, 2)
            candles[-1]["high"] = round(max(candles[-1]["high"], meta_market_price), 2)
            candles[-1]["low"] = round(min(candles[-1]["low"], meta_market_price), 2)
            volume_bars[-1]["is_up"] = candles[-1]["close"] >= candles[-1]["open"]

        # Accurate current price
        current_price = candles[-1]["close"]
        prev_close = None

        # Metadata calculations: accurately determine previous day's closing price (昨收價)
        if meta.get("fulldayChange") is not None:
            # Most accurate: regularMarketPrice - fulldayChange = exact yesterday close
            fullday_chg = float(meta["fulldayChange"])
            prev_close = round(current_price - fullday_chg, 2)
        elif is_intraday and meta.get("previousClose") and float(meta.get("previousClose")) > 0:
            prev_close = round(float(meta["previousClose"]), 2)
        elif not is_intraday and len(candles) >= 2:
            prev_close = float(candles[-2]["close"])
        elif is_intraday:
            # Look for last candle of previous day
            latest_date_prefix = candles[-1]["date"].split(" ")[0]
            prev_day_candles = [c for c in candles if not c["date"].startswith(latest_date_prefix)]
            if prev_day_candles:
                prev_close = float(prev_day_candles[-1]["close"])
            elif len(candles) >= 2:
                prev_close = float(candles[-2]["close"])

        # Fallback if still None
        if prev_close is None or prev_close <= 0:
            if len(candles) >= 2:
                prev_close = float(candles[-2]["close"])
            else:
                prev_close = float(candles[0]["open"])

        prev_close = round(float(prev_close), 2)

        # Accurate daily change & percent
        if meta.get("fulldayChange") is not None:
            change = round(float(meta["fulldayChange"]), 2)
        else:
            change = round(current_price - prev_close, 2)

        if meta.get("regularMarketChangePercent") is not None:
            change_pct = round(float(meta["regularMarketChangePercent"]), 2)
        elif meta.get("fulldayChangePercent") is not None:
            change_pct = round(float(meta["fulldayChangePercent"]), 2)
        elif prev_close > 0:
            change_pct = round((change / prev_close) * 100, 2)
        else:
            change_pct = 0.0

        # Taiwan market limit up (+10%) & limit down (-10%) with official tick sizes
        limit_up, limit_down = calc_tw_limits(prev_close)

        stock_info = get_stock_info(symbol)
        
        # Taiwan lot = 1,000 shares
        latest_vol_shares = candles[-1]["volume"]
        latest_vol_lots = round(latest_vol_shares / 1000, 1)

        # High / Low calculation for the current trading day
        day_high = meta.get("regularMarketDayHigh")
        if day_high is None or float(day_high) < candles[-1]["high"]:
            day_high = candles[-1]["high"]
        day_high = round(float(day_high), 2)

        day_low = meta.get("regularMarketDayLow")
        if day_low is None or float(day_low) > candles[-1]["low"]:
            day_low = candles[-1]["low"]
        day_low = round(float(day_low), 2)

        day_open = meta.get("regularMarketOpen") or candles[-1]["open"]
        day_open = round(float(day_open), 2)

        # Extract dividend events
        raw_divs = result.get("events", {}).get("dividends", {})
        dividends = []
        for ts_key, div_item in raw_divs.items():
            try:
                div_ts = int(div_item.get("date", ts_key))
                div_dt = datetime.fromtimestamp(div_ts, tz=tz_tw)
                dividends.append({
                    "time": div_dt.strftime("%Y-%m-%d"),
                    "amount": round(float(div_item.get("amount", 0.0)), 2),
                    "date": div_dt.strftime("%Y-%m-%d")
                })
            except Exception:
                pass
        dividends = sorted(dividends, key=lambda x: x["time"])

        # Safely fetch official fundamentals (PE, PB, Yield) & Institutional Flow without blocking
        code_only = stock_info.get("code", symbol.split(".")[0])
        try:
            fund = get_stock_fundamentals(code_only)
        except Exception:
            fund = {"peRatio": None, "pbRatio": None, "dividendYield": None}

        try:
            inst = get_institutional_flow(code_only)
        except Exception:
            inst = {
                "foreignLots": 0.0, "trustLots": 0.0, "dealerLots": 0.0, "totalLots": 0.0,
                "trustConsecutiveDays": 0, "isTrustFocus": False, "summaryText": "暫無法取得法人即時進出"
            }

        try:
            inst_flow_series = get_simulated_historical_institutional_flow(candles, inst)
        except Exception:
            inst_flow_series = []

        # Safely fetch ETF Premium/Discount & Spread analysis if target is an ETF
        etf_data = None
        if is_etf(symbol) or is_etf_code(code_only, stock_info.get("industry", "")):
            try:
                etf_data = get_complete_etf_analysis(code_only, stock_info.get("market", "TWSE"))
            except Exception as e:
                print(f"Error fetching ETF data for {code_only}: {e}")

        # Determine best display name
        display_name = stock_info.get("name", symbol)
        if etf_data and etf_data.get("name") and not etf_data["name"].startswith("ETF "):
            display_name = etf_data["name"]

        summary = {
            "symbol": symbol,
            "code": code_only,
            "name": display_name,
            "market": stock_info.get("market", "TWSE"),
            "industry": stock_info.get("industry", "台股"),
            "currency": meta.get("currency", "TWD"),
            "regularMarketPrice": current_price,
            "previousClose": prev_close,
            "change": change,
            "changePercent": change_pct,
            "high": round(float(day_high), 2),
            "low": round(float(day_low), 2),
            "open": round(float(day_open), 2),
            "limitUp": limit_up,
            "limitDown": limit_down,
            "volumeShares": latest_vol_shares,
            "volumeLots": latest_vol_lots,
            "peRatio": fund.get("peRatio"),
            "pbRatio": fund.get("pbRatio"),
            "dividendYield": fund.get("dividendYield"),
            "institutional": inst,
            "etf": etf_data,
            "dividends": dividends[-8:],
            "lastUpdate": candles[-1]["date"]
        }

        output = {
            "summary": summary,
            "candles": candles,
            "volume": volume_bars,
            "institutional": inst_flow_series,
            "dividends": dividends,
            "is_intraday": is_intraday,
            "interval": interval,
            "range": time_range
        }

        # Save to cache
        _CACHE[cache_key] = (now, output)
        return output

    except Exception as e:
        print(f"Data fetch error for {symbol}: {e}, activating offline fallback.")
        return generate_offline_fallback_data(symbol_or_code, interval, time_range, error_reason=str(e))

def generate_offline_fallback_data(
    symbol_or_code: str,
    interval: str = "1d",
    time_range: str = "1y",
    error_reason: str = ""
) -> Dict[str, Any]:
    """
    High-fidelity offline fallback candle generator for Taiwan stocks.
    Ensures that when external Yahoo Finance / TWSE network is restricted,
    the user interface never crashes, blanks out, or shows empty charts.
    """
    stock_info = get_stock_info(symbol_or_code)
    code = stock_info.get("code", str(symbol_or_code).split(".")[0])
    symbol = stock_info.get("symbol", f"{code}.TW")
    name = stock_info.get("name", f"台股 {code}")
    market = stock_info.get("market", "TWSE")
    industry = stock_info.get("industry", "半導體業")

    # Base price calibration for popular Taiwan stocks
    base_price_map = {
        "2330": 2410.0, "2317": 256.0, "2454": 4415.0, "2308": 480.0,
        "2382": 380.0, "0050": 108.0, "2603": 233.0, "8069": 148.5,
        "3231": 155.0, "2303": 58.0, "2881": 92.0, "2882": 65.0
    }
    base_p = base_price_map.get(code, 100.0)

    tz_tw = timezone(timedelta(hours=8))
    today = datetime.now(tz_tw)

    is_intraday = interval in ["5m", "15m", "60m"]
    total_bars = 48 if is_intraday else (180 if time_range in ["1y", "2y"] else 60)

    candles = []
    volume_bars = []
    curr_p = base_p

    # Deterministic pseudo-random walk
    for i in range(total_bars, 0, -1):
        if is_intraday:
            bar_dt = today - timedelta(minutes=i * (5 if interval == "5m" else (15 if interval == "15m" else 60)))
            t_val = int(bar_dt.timestamp())
            d_str = bar_dt.strftime("%Y-%m-%d %H:%M")
        else:
            bar_dt = today - timedelta(days=int(i * 1.45))
            if bar_dt.weekday() >= 5:  # skip weekends
                continue
            t_val = bar_dt.strftime("%Y-%m-%d")
            d_str = t_val

        seed = (hash(f"{code}_{i}") % 100) / 100.0 - 0.48
        step = curr_p * seed * 0.02
        c = round(curr_p + step, 2)
        o = round(curr_p, 2)
        h = round(max(o, c) + abs(step) * 0.4 + 0.5, 2)
        l = round(min(o, c) - abs(step) * 0.4 - 0.5, 2)
        v = int(abs(seed * 2000000) + 1200000)

        candles.append({
            "time": t_val,
            "date": d_str,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v
        })
        volume_bars.append({
            "time": t_val,
            "value": v,
            "is_up": c >= o
        })
        curr_p = c

    if not candles:
        candles = [{
            "time": today.strftime("%Y-%m-%d"),
            "date": today.strftime("%Y-%m-%d"),
            "open": base_p, "high": base_p + 5, "low": base_p - 5, "close": base_p + 2, "volume": 1000000
        }]
        volume_bars = [{"time": candles[0]["time"], "value": 1000000, "is_up": True}]

    last_c = candles[-1]["close"]
    prev_c = candles[-2]["close"] if len(candles) > 1 else candles[0]["open"]
    chg = round(last_c - prev_c, 2)
    chg_pct = round((chg / prev_c) * 100, 2) if prev_c > 0 else 0.0

    summary = {
        "symbol": symbol,
        "code": code,
        "name": name,
        "market": market,
        "industry": industry,
        "currency": "TWD",
        "regularMarketPrice": last_c,
        "previousClose": prev_c,
        "change": chg,
        "changePercent": chg_pct,
        "high": candles[-1]["high"],
        "low": candles[-1]["low"],
        "open": candles[-1]["open"],
        "limitUp": round(prev_c * 1.10, 2),
        "limitDown": round(prev_c * 0.90, 2),
        "volumeShares": candles[-1]["volume"],
        "volumeLots": round(candles[-1]["volume"] / 1000, 1),
        "peRatio": 25.4,
        "pbRatio": 6.8,
        "dividendYield": 2.8,
        "institutional": {
            "foreignLots": 1250.0, "trustLots": 480.0, "dealerLots": 120.0, "totalLots": 1850.0,
            "trustConsecutiveDays": 3, "isTrustFocus": True, "summaryText": "投信連續買超 3 日 (示範數據)"
        },
        "dividends": [
            {"time": "2024-03-18", "amount": 3.5, "date": "2024-03-18"},
            {"time": "2024-06-13", "amount": 4.0, "date": "2024-06-13"}
        ],
        "lastUpdate": candles[-1]["date"],
        "isFallback": True,
        "notice": f"外部行情連線暫時受限 ({error_reason})，現正以本機示範數據提供完整技術分析。" if error_reason else ""
    }

    return {
        "summary": summary,
        "candles": candles,
        "volume": volume_bars,
        "institutional": get_simulated_historical_institutional_flow(candles, summary["institutional"]),
        "dividends": summary["dividends"],
        "is_intraday": is_intraday,
        "interval": interval,
        "range": time_range
    }

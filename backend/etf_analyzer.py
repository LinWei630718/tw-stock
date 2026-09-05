"""
ETF Analysis Engine for Taiwan Stock Market
Provides real-time Premium/Discount (折溢價), Net Asset Value (淨值),
Bid-Ask Spread (買賣價差), Liquidity check, and combined Technical Timing Analysis (MACD, MA).
"""

import urllib.request
import ssl
import json
import time
from typing import Dict, Any, Optional, List

# Cache variables for TWSE all_etf data
_ALL_ETF_CACHE: Dict[str, Any] = {}
_ALL_ETF_CACHE_TIME: float = 0
CACHE_TTL_SECONDS: float = 60.0  # 1 minute cache for real-time responsiveness

def _create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def is_etf_code(code: str, industry: str = "") -> bool:
    """Check if code or industry represents a Taiwan ETF"""
    c = str(code).strip()
    if c.startswith("00"):
        return True
    if "ETF" in industry.upper() or "指數股票型" in industry:
        return True
    return False

def fetch_all_etf_map() -> Dict[str, Dict[str, Any]]:
    """
    Fetch all TWSE/TPEx ETF premium/discount data from official MIS source.
    Endpoint: https://mis.twse.com.tw/stock/data/all_etf.txt
    """
    global _ALL_ETF_CACHE, _ALL_ETF_CACHE_TIME
    now = time.time()
    if _ALL_ETF_CACHE and (now - _ALL_ETF_CACHE_TIME) < CACHE_TTL_SECONDS:
        return _ALL_ETF_CACHE

    url = "https://mis.twse.com.tw/stock/data/all_etf.txt"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    })

    etf_map = {}
    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            raw_text = resp.read().decode("utf-8")
            data = json.loads(raw_text)

        for group in data.get("a1", []):
            for m in group.get("msgArray", []):
                code = str(m.get("a", "")).strip()
                if not code:
                    continue

                # Parse estimated NAV, market price, premium/discount
                # e: market price, f: diff / premium amount, g: premium/discount %, h: estimated NAV, i: date, j: time
                try:
                    market_price = float(m.get("e", 0.0))
                except Exception:
                    market_price = 0.0

                try:
                    est_nav = float(m.get("h", 0.0))
                except Exception:
                    est_nav = 0.0

                try:
                    diff = float(m.get("f", 0.0))
                except Exception:
                    diff = round(market_price - est_nav, 2) if (market_price and est_nav) else 0.0

                try:
                    prem_disc_pct = float(m.get("g", 0.0))
                except Exception:
                    prem_disc_pct = round((diff / est_nav) * 100, 2) if est_nav > 0 else 0.0

                raw_name = str(m.get("b", "")).strip()
                clean_name = raw_name.split("(")[0].split("（")[0].strip()

                etf_map[code] = {
                    "code": code,
                    "name": clean_name,
                    "marketPrice": market_price,
                    "nav": est_nav,
                    "diff": diff,
                    "premiumDiscountPercent": prem_disc_pct,
                    "date": m.get("i", ""),
                    "time": m.get("j", "")
                }

        # Calibration for active ETFs
        active_etf_map = {
            "00403A": "主動統一升級50",
            "00405A": "主動富邦台灣龍耀",
            "00406A": "主動中信台灣收益",
            "00407A": "主動凱基台灣",
            "00408A": "主動第一金優股息",
            "00409A": "主動復華全球50",
            "00400A": "主動國泰動能高息",
            "00401A": "主動摩根台灣鑫收",
            "00402A": "主動安聯美國科技",
            "00404A": "主動聯博動能50",
            "00411A": "主動統一前沿科技"
        }
        for ac, aname in active_etf_map.items():
            if ac in etf_map:
                etf_map[ac]["name"] = aname

        if etf_map:
            _ALL_ETF_CACHE = etf_map
            _ALL_ETF_CACHE_TIME = now
            return etf_map

    except Exception as e:
        print(f"Failed to fetch all_etf.txt from TWSE MIS: {e}")

    return _ALL_ETF_CACHE or {}

def fetch_etf_orderbook_spread(code: str, market: str = "TWSE") -> Dict[str, Any]:
    """
    Fetch best bid and ask to calculate bid-ask spread and spread percentage.
    """
    code_clean = str(code).split(".")[0]
    ex_prefix = "otc" if market.upper() in ["TPEX", "OTC"] else "tse"
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_prefix}_{code_clean}.tw&json=1&delay=0"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    result = {
        "bestBid": None,
        "bestAsk": None,
        "spread": None,
        "spreadPercent": None,
        "volume": None,
        "liquidityLevel": "正常"
    }

    try:
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg_list = data.get("msgArray", [])
            if not msg_list:
                return result

            m = msg_list[0]
            bids = [float(p) for p in m.get("b", "").split("_") if p and p != "-"]
            asks = [float(p) for p in m.get("a", "").split("_") if p and p != "-"]

            if bids and asks:
                best_bid = bids[0]
                best_ask = asks[0]
                spread = round(best_ask - best_bid, 4)
                spread_pct = round((spread / best_bid) * 100, 3) if best_bid > 0 else 0.0

                result["bestBid"] = best_bid
                result["bestAsk"] = best_ask
                result["spread"] = spread
                result["spreadPercent"] = spread_pct

            try:
                v = int(m.get("v", 0))
                result["volume"] = v
            except Exception:
                pass

            # Evaluate liquidity rating based on spread percent
            if result["spreadPercent"] is not None:
                if result["spreadPercent"] <= 0.08:
                    result["liquidityLevel"] = "極佳 (極窄價差)"
                elif result["spreadPercent"] <= 0.20:
                    result["liquidityLevel"] = "良好"
                elif result["spreadPercent"] <= 0.40:
                    result["liquidityLevel"] = "普通 (建議限價)"
                else:
                    result["liquidityLevel"] = "偏寬 (流動性注意)"

    except Exception as e:
        print(f"Error fetching orderbook spread for {code}: {e}")

    return result

def evaluate_etf_timing(
    etf_info: Dict[str, Any],
    candles: List[Dict[str, Any]],
    indicators: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combined ETF Timing Decision Matrix:
    Evaluates Premium/Discount, Spread, Volume, Moving Averages (5MA/20MA), and MACD.
    Returns:
      - action: '強烈買進 (Strong Buy)' | '偏多佈局 (Accumulate)' | '中性觀望 (Wait)' | '溢價警戒 (Caution)' | '逢高減碼 (Trim)'
      - actionColor: CSS color
      - score: 0 ~ 100
      - premiumStatus: '折價 (物超所值)' | '合理' | '高溢價 (有追高風險)'
      - reasons: List of key factors
      - spreadDesc: description of friction cost
    """
    prem_pct = etf_info.get("premiumDiscountPercent")
    if prem_pct is None:
        prem_pct = 0.0

    spread_pct = etf_info.get("spreadPercent")
    reasons = []
    bull_signals = 0
    bear_signals = 0

    # 1. Premium / Discount Assessment
    if prem_pct < -0.4:
        premium_status = f"大幅折價 ({prem_pct}%)"
        reasons.append(f"市價低於淨值 {abs(prem_pct)}%，存在安全邊際與估值收斂優勢")
        bull_signals += 2
    elif prem_pct < -0.1:
        premium_status = f"輕微折價 ({prem_pct}%)"
        reasons.append(f"市價小幅折價 {abs(prem_pct)}%，交易價格公允偏甜")
        bull_signals += 1
    elif prem_pct <= 0.3:
        premium_status = f"合理區間 ({prem_pct > 0 and '+' or ''}{prem_pct}%)"
        reasons.append("市價貼近淨值，無異常追高溢價風險")
    elif prem_pct <= 0.8:
        premium_status = f"偏高溢價 (+{prem_pct}%)"
        reasons.append(f"溢價已達 +{prem_pct}%，建議避免市價追高，留意造市商申購收斂")
        bear_signals += 1
    else:
        premium_status = f"⚠️ 嚴重溢價 (+{prem_pct}%)"
        reasons.append(f"嚴重溢價達 +{prem_pct}%！買進成本顯著高於真實淨值，強烈警惕回檔修正")
        bear_signals += 3

    # 2. Spread & Liquidity Assessment
    if spread_pct is not None:
        if spread_pct <= 0.08:
            reasons.append(f"買賣價差僅 {spread_pct}%，造市流動性極佳，進出交易成本極低")
            bull_signals += 0.5
        elif spread_pct > 0.30:
            reasons.append(f"買賣價差達 {spread_pct}% 偏寬，請使用限價委託，勿以市價單進出")
            bear_signals += 0.5

    # 3. Technical Timing (Moving Averages & MACD)
    ma = indicators.get("ma", {})
    ma5_series = ma.get("ma5", [])
    ma20_series = ma.get("ma20", [])
    macd = indicators.get("macd", {})
    bar_series = macd.get("bar", [])
    dif_series = macd.get("dif", [])
    dea_series = macd.get("dea", [])

    if candles and len(candles) >= 2:
        c_curr = candles[-1]["close"]
        c_prev = candles[-2]["close"]

        # Check MA20 (Monthly trend line)
        if ma20_series:
            v_ma20 = ma20_series[-1]["value"]
            if c_curr > v_ma20:
                bull_signals += 1.5
                if ma5_series and ma5_series[-1]["value"] > v_ma20:
                    reasons.append("站上 20 日月線且 5MA > 20MA，中期趨勢維持多頭波段架構")
                else:
                    reasons.append("股價穩站 20 日月線上，中多格局支撐強勁")
            else:
                bear_signals += 1.5
                reasons.append("股價位於 20 日月線下方，技術面處於整理或弱勢修正")

        # Check MACD
        if bar_series and len(bar_series) >= 2:
            osc_curr = bar_series[-1]["value"]
            osc_prev = bar_series[-2]["value"]

            if osc_curr > 0 and osc_curr > osc_prev:
                bull_signals += 1.5
                reasons.append("MACD 紅柱持續放大，動能強勁攻擊中")
            elif osc_prev <= 0 and osc_curr > 0:
                bull_signals += 2
                reasons.append("MACD 柱狀體翻紅黃金交叉，買點動能確立")
            elif osc_curr < 0 and osc_curr < osc_prev:
                bear_signals += 1.5
                reasons.append("MACD 綠柱放大，短線賣壓仍待消化")
            elif osc_prev >= 0 and osc_curr < 0:
                bear_signals += 2
                reasons.append("MACD 轉綠死亡交叉，宜防短線回測")

    # 4. Synthesize Decision Score & Action
    net_score = 50 + (bull_signals - bear_signals) * 12
    final_score = max(10, min(95, int(round(net_score))))

    if prem_pct > 0.8:
        # Severe premium forces caution regardless of technical strength
        action = "溢價警戒 (Caution / Trim)"
        action_color = "#fa8c16"
    elif final_score >= 75:
        action = "強烈買進 (Strong Buy)"
        action_color = "#ef5350"
    elif final_score >= 60:
        action = "偏多佈局 (Accumulate)"
        action_color = "#ff7875"
    elif final_score >= 45:
        action = "中性觀望 (Hold / Wait)"
        action_color = "#b0bec5"
    elif final_score >= 30:
        action = "逢高調節 (Trim / Hedge)"
        action_color = "#36cfc9"
    else:
        action = "停損觀望 (Bearish / Exit)"
        action_color = "#52c41a"

    return {
        "score": final_score,
        "action": action,
        "actionColor": action_color,
        "premiumStatus": premium_status,
        "reasons": reasons,
        "rawSignals": {
            "bull": bull_signals,
            "bear": bear_signals,
            "premiumDiscount": prem_pct,
            "spreadPercent": spread_pct
        }
    }

def get_complete_etf_analysis(
    code: str,
    market: str = "TWSE",
    candles: Optional[List[Dict[str, Any]]] = None,
    indicators: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    High-level API to retrieve unified ETF metrics and timing.
    Returns None if stock is not an ETF.
    """
    code_clean = str(code).split(".")[0]
    all_map = fetch_all_etf_map()
    etf_row = all_map.get(code_clean)

    # If code starts with 00 but not yet in all_map, create basic record
    if not etf_row and not code_clean.startswith("00"):
        return None

    if not etf_row:
        etf_row = {
            "code": code_clean,
            "name": f"ETF {code_clean}",
            "marketPrice": 0.0,
            "nav": 0.0,
            "diff": 0.0,
            "premiumDiscountPercent": 0.0,
            "date": "",
            "time": ""
        }

    # Fetch live order book spread
    spread_info = fetch_etf_orderbook_spread(code_clean, market)

    merged_etf = {
        **etf_row,
        **spread_info
    }

    # Calculate timing diagnosis if candles and indicators provided
    timing = None
    if candles and indicators:
        timing = evaluate_etf_timing(merged_etf, candles, indicators)
    merged_etf["timing"] = timing

    return merged_etf

"""
Technical Diagnostic & Multi-Stock Screener Module
Generates comprehensive technical diagnostic scores, signals, and executes strategy scans.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import List, Dict, Any
from tw_stocks import POPULAR_CATEGORIES, get_stock_info
from data_fetcher import fetch_stock_chart_data
from indicators import calculate_indicators

def diagnose_stock(candles: List[Dict[str, Any]], indicators: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform a multi-dimensional technical diagnosis for a single stock.
    Returns:
    - score (0 to 100)
    - rating ('強烈看多', '偏多震盪', '中立整理', '偏空震盪', '強烈看空')
    - signals (List of detected positive/negative signals)
    - dimensions: breakdown scores for Trend, Momentum, Volume, Volatility
    """
    if not candles or len(candles) < 20:
        return {
            "score": 50,
            "rating": "數據不足",
            "signals": [],
            "dimensions": {"trend": 50, "momentum": 50, "volume": 50, "volatility": 50}
        }

    latest = candles[-1]
    prev = candles[-2]
    c_curr = latest["close"]
    c_prev = prev["close"]
    vol_curr = latest["volume"]

    signals = []
    bull_points = 0
    bear_points = 0
    total_checks = 0

    # 1. Moving Averages Analysis
    ma = indicators.get("ma", {})
    ma5 = ma.get("ma5", [])
    ma10 = ma.get("ma10", [])
    ma20 = ma.get("ma20", [])
    ma60 = ma.get("ma60", [])

    trend_score = 50
    if ma5 and ma20:
        v_ma5 = ma5[-1]["value"]
        v_ma20 = ma20[-1]["value"]
        v_ma60 = ma60[-1]["value"] if ma60 else None

        # Price vs MA20
        total_checks += 1
        if c_curr > v_ma20:
            bull_points += 1
            if c_prev <= ma20[-2]["value"] if len(ma20) > 1 else False:
                signals.append({"type": "bull", "tag": "均線突破", "text": "股價今日帶量向上突破 20 日月線"})
        else:
            bear_points += 1

        # MA Alignment
        if v_ma60:
            total_checks += 1
            if v_ma5 > v_ma20 > v_ma60:
                bull_points += 1.5
                trend_score = 85
                signals.append({"type": "bull", "tag": "多頭排列", "text": "5MA > 20MA > 60MA 均線群呈現標準多頭排列"})
            elif v_ma5 < v_ma20 < v_ma60:
                bear_points += 1.5
                trend_score = 25
                signals.append({"type": "bear", "tag": "空頭排列", "text": "5MA < 20MA < 60MA 均線呈空頭排列，逢反彈宜謹慎"})
            else:
                trend_score = 55
                signals.append({"type": "neutral", "tag": "均線糾結", "text": "短中天期均線糾結，靜待方向表態"})

    # 2. KD (9, 3, 3) Analysis
    kd = indicators.get("kd", {})
    k_list = kd.get("k", [])
    d_list = kd.get("d", [])
    momentum_score = 50

    if len(k_list) >= 2 and len(d_list) >= 2:
        k_curr = k_list[-1]["value"]
        d_curr = d_list[-1]["value"]
        k_prev = k_list[-2]["value"]
        d_prev = d_list[-2]["value"]

        total_checks += 1
        # Golden cross
        if k_prev <= d_prev and k_curr > d_curr:
            bull_points += 1.5
            momentum_score = 80
            if k_curr < 35:
                signals.append({"type": "bull", "tag": "KD低檔金叉", "text": f"KD在超賣區 ({round(k_curr,1)}) 形成黃金交叉，買點浮現"})
            else:
                signals.append({"type": "bull", "tag": "KD金叉", "text": f"KD指標向上黃金交叉 (K={round(k_curr,1)})"})
        # Death cross
        elif k_prev >= d_prev and k_curr < d_curr:
            bear_points += 1.5
            momentum_score = 30
            if k_curr > 75:
                signals.append({"type": "bear", "tag": "KD高檔死叉", "text": f"KD在超買區 ({round(k_curr,1)}) 形成死亡交叉，提防獲利回吐"})
            else:
                signals.append({"type": "bear", "tag": "KD死叉", "text": f"KD指標向下跌破形成死亡交叉 (K={round(k_curr,1)})"})
        else:
            if k_curr > 80 and d_curr > 80:
                signals.append({"type": "neutral", "tag": "KD超買高檔鈍化", "text": f"KD處於超買區 ({round(k_curr,1)})，留意追高風險"})
            elif k_curr < 20 and d_curr < 20:
                signals.append({"type": "bull", "tag": "KD嚴重超賣", "text": f"KD超賣區 ({round(k_curr,1)})，醞釀短線強彈契機"})

    # 3. MACD Analysis
    macd = indicators.get("macd", {})
    bar_list = macd.get("bar", [])
    dif_list = macd.get("dif", [])
    dea_list = macd.get("dea", [])

    if len(bar_list) >= 2:
        bar_curr = bar_list[-1]["value"]
        bar_prev = bar_list[-2]["value"]

        total_checks += 1
        if bar_prev <= 0 and bar_curr > 0:
            bull_points += 1.2
            signals.append({"type": "bull", "tag": "MACD紅柱初生", "text": "MACD柱狀體由負翻正，多方發動攻擊"})
        elif bar_curr > 0 and bar_curr > bar_prev:
            bull_points += 0.8
            signals.append({"type": "bull", "tag": "MACD紅柱放大", "text": "MACD紅柱持續加長，多頭動能充沛"})
        elif bar_prev >= 0 and bar_curr < 0:
            bear_points += 1.2
            signals.append({"type": "bear", "tag": "MACD綠柱初生", "text": "MACD柱狀體由正轉負，短線轉弱"})
        elif bar_curr < 0 and bar_curr < bar_prev:
            bear_points += 0.8

    # 4. Bollinger Bands Analysis
    bb = indicators.get("bollinger", {})
    bb_upper = bb.get("upper", [])
    bb_lower = bb.get("lower", [])
    bb_bw = bb.get("bandwidth", [])
    volatility_score = 50

    if bb_upper and bb_lower:
        u_val = bb_upper[-1]["value"]
        l_val = bb_lower[-1]["value"]
        bw_val = bb_bw[-1]["value"] if bb_bw else 10.0

        if bw_val < 8.0:
            signals.append({"type": "neutral", "tag": "布林極度收斂", "text": f"布林通道帶寬僅 {bw_val}%，進入壓縮即將大變盤"})
            volatility_score = 65

        if c_curr > u_val:
            bull_points += 1
            signals.append({"type": "bull", "tag": "突破布林上軌", "text": "強勢突破布林通道上軌，展現強攻氣勢"})
        elif c_curr < l_val:
            bear_points += 0.5
            signals.append({"type": "neutral", "tag": "跌破布林下軌", "text": "回測跌破布林下軌，短線極度超跌"})
        elif len(candles) >= 2 and candles[-2]["low"] <= l_val and c_curr > l_val:
            bull_points += 1
            signals.append({"type": "bull", "tag": "布林下軌支撐反彈", "text": "碰觸布林下軌獲得強支撐並強勁反彈"})

    # 5. Volume Analysis
    vma = indicators.get("vma", {})
    vma5 = vma.get("vma5", [])
    volume_score = 50
    if vma5:
        avg_vol = vma5[-1]["value"]
        if avg_vol > 0:
            ratio = vol_curr / avg_vol
            total_checks += 1
            if ratio >= 2.0 and c_curr > c_prev:
                bull_points += 1.5
                volume_score = 90
                signals.append({"type": "bull", "tag": "爆量長紅", "text": f"成交量為5日均量之 {round(ratio, 1)} 倍，買盤積極湧入"})
            elif ratio >= 1.5 and c_curr > c_prev:
                bull_points += 0.8
                volume_score = 75
                signals.append({"type": "bull", "tag": "量增價揚", "text": "量增價揚，健康多頭換手走勢"})
            elif ratio >= 2.0 and c_curr < c_prev:
                bear_points += 1.5
                volume_score = 25
                signals.append({"type": "bear", "tag": "爆量長黑", "text": f"放量下殺 ({round(ratio, 1)} 倍量)，賣壓沈重請嚴設停損"})
            elif ratio < 0.5:
                volume_score = 45
                signals.append({"type": "neutral", "tag": "量能急凍", "text": "成交量萎縮低於均量 50%，市場觀望氣氛濃厚"})

    # 6. RSI (6) Check
    rsi = indicators.get("rsi", {})
    rsi6 = rsi.get("rsi6", [])
    if rsi6:
        r6 = rsi6[-1]["value"]
        if r6 > 80:
            bear_points += 0.8
            signals.append({"type": "neutral", "tag": "RSI過熱警戒", "text": f"RSI(6) = {r6} 已達嚴重過熱警戒區"})
        elif r6 < 20:
            bull_points += 1
            signals.append({"type": "bull", "tag": "RSI超跌轉折", "text": f"RSI(6) = {r6} 進入嚴重超賣區，醞釀技術性反彈"})

    # Final Composite Score: 0 to 100
    if total_checks == 0:
        score = 50
    else:
        net = bull_points - bear_points
        # Map net to 0~100 with baseline 50
        raw_score = 50 + (net * 11)
        score = max(5, min(95, int(round(raw_score))))

    if score >= 75:
        rating = "強烈看多 (Strong Buy)"
        rating_color = "#ef5350"
    elif score >= 60:
        rating = "偏多震盪 (Bullish)"
        rating_color = "#ff8a80"
    elif score >= 45:
        rating = "中立整理 (Neutral)"
        rating_color = "#b0bec5"
    elif score >= 30:
        rating = "偏空震盪 (Bearish)"
        rating_color = "#80cbc4"
    else:
        rating = "強烈看空 (Strong Sell)"
        rating_color = "#26a69a"

    return {
        "score": score,
        "rating": rating,
        "rating_color": rating_color,
        "signals": signals,
        "dimensions": {
            "trend": trend_score,
            "momentum": momentum_score,
            "volume": volume_score,
            "volatility": volatility_score
        }
    }

# Preset scanner candidate pool (~40 leading liquid TW stocks)
SCANNER_UNIVERSE = [
    "2330", "2317", "2454", "2308", "2382", "3231", "2376", "3017",
    "3324", "6669", "2356", "3653", "2059", "3443", "0050", "0056",
    "00878", "00919", "2603", "2609", "2615", "2618", "8069", "3293",
    "2881", "2882", "2303", "2357", "1519", "1513", "1609", "2379"
]

def run_strategy_screener(strategy_id: str) -> List[Dict[str, Any]]:
    """
    Scans candidate stocks based on selected strategy.
    Strategy IDs:
    - 'kd_golden_cross': 低檔KD黃金交叉 (K < 35 且 K向上穿D)
    - 'ma_bullish_breakout': 均線突破多頭 (收盤價 > 20MA 且 5MA > 20MA)
    - 'bb_lower_rebound': 布林下軌支撐強彈
    - 'macd_turn_positive': MACD 柱狀體翻紅轉折
    - 'volume_breakout': 爆量長紅攻擊 (成交量 > 2倍5日均量且漲幅 > 2.5%)
    """
    matched = []

    for code in SCANNER_UNIVERSE:
        data = fetch_stock_chart_data(code, interval="1d", time_range="6mo", use_cache=True)
        if "error" in data or not data.get("candles") or len(data["candles"]) < 25:
            continue

        candles = data["candles"]
        ind = calculate_indicators(candles)
        summary = data["summary"]

        is_match = False
        match_reason = ""

        if strategy_id == "kd_golden_cross":
            k = ind.get("kd", {}).get("k", [])
            d = ind.get("kd", {}).get("d", [])
            if len(k) >= 2 and len(d) >= 2:
                if k[-2]["value"] <= d[-2]["value"] and k[-1]["value"] > d[-1]["value"] and k[-1]["value"] < 40:
                    is_match = True
                    match_reason = f"KD金叉 (K={k[-1]['value']}, D={d[-1]['value']})"

        elif strategy_id == "ma_bullish_breakout":
            ma5 = ind.get("ma", {}).get("ma5", [])
            ma20 = ind.get("ma", {}).get("ma20", [])
            if len(ma5) >= 2 and len(ma20) >= 2 and len(candles) >= 2:
                c_now = candles[-1]["close"]
                c_old = candles[-2]["close"]
                m20_now = ma20[-1]["value"]
                m20_old = ma20[-2]["value"]
                if c_now > m20_now and (c_old <= m20_old or ma5[-1]["value"] > m20_now):
                    is_match = True
                    match_reason = f"站上月線 (股價 {c_now} > MA20 {m20_now})"

        elif strategy_id == "bb_lower_rebound":
            bb_low = ind.get("bollinger", {}).get("lower", [])
            if bb_low and len(candles) >= 2:
                low_lim = bb_low[-1]["value"]
                if candles[-1]["low"] <= low_lim and candles[-1]["close"] > low_lim and candles[-1]["close"] >= candles[-1]["open"]:
                    is_match = True
                    match_reason = f"觸下軌收紅反彈 (低點 {candles[-1]['low']} ≤ 下軌 {low_lim})"

        elif strategy_id == "macd_turn_positive":
            bars = ind.get("macd", {}).get("bar", [])
            if len(bars) >= 2:
                if bars[-2]["value"] <= 0 and bars[-1]["value"] > 0:
                    is_match = True
                    match_reason = f"MACD紅柱初生 (OSC: {bars[-2]['value']} → +{bars[-1]['value']})"

        elif strategy_id == "volume_breakout":
            vma5 = ind.get("vma", {}).get("vma5", [])
            if vma5:
                v_curr = candles[-1]["volume"]
                v_avg = vma5[-1]["value"]
                chg_pct = summary["changePercent"]
                if v_avg > 0 and (v_curr / v_avg >= 1.8) and chg_pct >= 2.0:
                    is_match = True
                    ratio = round(v_curr / v_avg, 1)
                    match_reason = f"爆量攻擊 ({ratio}倍量，漲幅 +{chg_pct}%)"

        if is_match:
            matched.append({
                "code": summary["code"],
                "symbol": summary["symbol"],
                "name": summary["name"],
                "industry": summary["industry"],
                "price": summary["regularMarketPrice"],
                "change": summary["change"],
                "changePercent": summary["changePercent"],
                "volumeLots": summary["volumeLots"],
                "matchReason": match_reason
            })

    return matched

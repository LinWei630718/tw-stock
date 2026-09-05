"""
Technical Indicators Calculation Module
Computes MA, Bollinger Bands, KD (9,3,3), MACD (12,26,9), RSI, Volume MA, and BIAS.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd

def calculate_indicators(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Given a list of candle dicts with keys: ['time', 'date', 'open', 'high', 'low', 'close', 'volume'],
    computes all standard Taiwan stock technical indicators.
    """
    if not candles:
        return {}

    df = pd.DataFrame(candles)
    times = df["time"].tolist()
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    volumes = df["volume"].values
    n = len(df)

    # 1. Moving Averages (MA5, MA10, MA20, MA60, MA120, MA240)
    def calc_ma(period: int):
        series = df["close"].rolling(window=period).mean()
        result = []
        for t, val in zip(times, series):
            if pd.notna(val):
                result.append({"time": t, "value": round(float(val), 2)})
        return result

    ma5 = calc_ma(5)
    ma10 = calc_ma(10)
    ma20 = calc_ma(20)
    ma60 = calc_ma(60)
    ma120 = calc_ma(120)
    ma240 = calc_ma(240)

    # Volume Moving Averages (VMA5, VMA20)
    def calc_vma(period: int):
        series = df["volume"].rolling(window=period).mean()
        result = []
        for t, val in zip(times, series):
            if pd.notna(val):
                result.append({"time": t, "value": round(float(val), 0)})
        return result

    vma5 = calc_vma(5)
    vma20 = calc_vma(20)

    # 2. Bollinger Bands (20, 2)
    bb_upper = []
    bb_middle = []
    bb_lower = []
    bb_bandwidth = []

    rolling_20 = df["close"].rolling(window=20)
    ma20_series = rolling_20.mean()
    std20_series = rolling_20.std(ddof=0)

    for i in range(n):
        t = times[i]
        m = ma20_series.iloc[i]
        s = std20_series.iloc[i]
        if pd.notna(m) and pd.notna(s):
            up = round(float(m + 2 * s), 2)
            mid = round(float(m), 2)
            low = round(float(m - 2 * s), 2)
            bw = round(float((up - low) / mid * 100), 2) if mid > 0 else 0.0

            bb_upper.append({"time": t, "value": up})
            bb_middle.append({"time": t, "value": mid})
            bb_lower.append({"time": t, "value": low})
            bb_bandwidth.append({"time": t, "value": bw})

    # 3. KD (9, 3, 3) - Taiwan Standard Formula
    # RSV = (Close - MinLow9) / (MaxHigh9 - MinLow9) * 100
    # K = 2/3 * K_prev + 1/3 * RSV
    # D = 2/3 * D_prev + 1/3 * K
    kd_k = []
    kd_d = []
    kd_rsv = []

    k_val = 50.0
    d_val = 50.0

    for i in range(n):
        t = times[i]
        start_idx = max(0, i - 8)
        window_high = np.max(highs[start_idx:i+1])
        window_low = np.min(lows[start_idx:i+1])

        if window_high - window_low == 0:
            rsv = 50.0
        else:
            rsv = (closes[i] - window_low) / (window_high - window_low) * 100.0

        if i >= 8:  # after full 9-period warmup
            k_val = (2.0 / 3.0) * k_val + (1.0 / 3.0) * rsv
            d_val = (2.0 / 3.0) * d_val + (1.0 / 3.0) * k_val
            kd_k.append({"time": t, "value": round(k_val, 2)})
            kd_d.append({"time": t, "value": round(d_val, 2)})
            kd_rsv.append({"time": t, "value": round(rsv, 2)})
        else:
            k_val = (2.0 / 3.0) * k_val + (1.0 / 3.0) * rsv
            d_val = (2.0 / 3.0) * d_val + (1.0 / 3.0) * k_val

    # 4. MACD (12, 26, 9)
    # EMA12, EMA26, DIF = EMA12 - EMA26, DEM/MACD9 = EMA9(DIF), OSC = DIF - DEM
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dem = dif.ewm(span=9, adjust=False).mean()
    osc = dif - dem

    macd_dif = []
    macd_dea = []
    macd_bar = []

    for i in range(n):
        t = times[i]
        dif_v = round(float(dif.iloc[i]), 3)
        dea_v = round(float(dem.iloc[i]), 3)
        bar_v = round(float(osc.iloc[i]), 3)

        macd_dif.append({"time": t, "value": dif_v})
        macd_dea.append({"time": t, "value": dea_v})
        macd_bar.append({
            "time": t,
            "value": bar_v,
            "color": "#ef5350" if bar_v >= 0 else "#26a69a"  # Taiwan: red is positive, green is negative
        })

    # 5. RSI (6, 12, 24)
    def calc_rsi(period: int):
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))

        result = []
        for i in range(period, n):
            val = rsi_series.iloc[i]
            if pd.notna(val):
                result.append({"time": times[i], "value": round(float(val), 2)})
            elif pd.isna(val) and gain.iloc[i] == 0 and loss.iloc[i] == 0:
                result.append({"time": times[i], "value": 50.0})
        return result

    rsi6 = calc_rsi(6)
    rsi12 = calc_rsi(12)
    rsi24 = calc_rsi(24)

    # 6. BIAS (20, 60)
    bias20 = []
    bias60 = []
    ma60_series = df["close"].rolling(window=60).mean()
    for i in range(n):
        t = times[i]
        c = closes[i]
        m20 = ma20_series.iloc[i]
        m60 = ma60_series.iloc[i]
        if pd.notna(m20) and m20 > 0:
            bias20.append({"time": t, "value": round(float((c - m20) / m20 * 100), 2)})
        if pd.notna(m60) and m60 > 0:
            bias60.append({"time": t, "value": round(float((c - m60) / m60 * 100), 2)})

    # 7. Fibonacci Retracement & Support/Resistance Levels
    # Lookback window for swing high/low (up to 90 bars)
    lookback = min(n, 90)
    window = candles[-lookback:]
    swing_high = float(max(c["high"] for c in window))
    swing_low = float(min(c["low"] for c in window))
    diff = swing_high - swing_low
    c_last = float(closes[-1]) if n > 0 else swing_high

    if diff > 0:
        fib_levels = [
            {"ratio": 0.0, "name": "壓力位 (高點)", "price": round(swing_high, 2), "color": "#ff4d4f", "lineStyle": 2},
            {"ratio": 0.236, "name": "Fib 23.6%", "price": round(swing_high - 0.236 * diff, 2), "color": "#ffa39e", "lineStyle": 1},
            {"ratio": 0.382, "name": "Fib 38.2%", "price": round(swing_high - 0.382 * diff, 2), "color": "#ffd591", "lineStyle": 1},
            {"ratio": 0.5, "name": "Fib 50.0% (中位)", "price": round(swing_high - 0.5 * diff, 2), "color": "#1890ff", "lineStyle": 0},
            {"ratio": 0.618, "name": "Fib 61.8% (黃金率)", "price": round(swing_high - 0.618 * diff, 2), "color": "#52c41a", "lineStyle": 0},
            {"ratio": 0.786, "name": "Fib 78.6%", "price": round(swing_high - 0.786 * diff, 2), "color": "#87e8de", "lineStyle": 1},
            {"ratio": 1.0, "name": "支撐位 (低點)", "price": round(swing_low, 2), "color": "#00b96b", "lineStyle": 2}
        ]
    else:
        fib_levels = []

    fibonacci = {
        "swingHigh": round(swing_high, 2),
        "swingLow": round(swing_low, 2),
        "range": round(diff, 2),
        "lookbackBars": lookback,
        "distToHighPct": round(((swing_high - c_last) / c_last) * 100, 2) if c_last > 0 else 0.0,
        "distToLowPct": round(((c_last - swing_low) / c_last) * 100, 2) if c_last > 0 else 0.0,
        "levels": fib_levels
    }

    return {
        "ma": {
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
            "ma120": ma120,
            "ma240": ma240
        },
        "vma": {
            "vma5": vma5,
            "vma20": vma20
        },
        "bollinger": {
            "upper": bb_upper,
            "middle": bb_middle,
            "lower": bb_lower,
            "bandwidth": bb_bandwidth
        },
        "kd": {
            "k": kd_k,
            "d": kd_d,
            "rsv": kd_rsv
        },
        "macd": {
            "dif": macd_dif,
            "dea": macd_dea,
            "bar": macd_bar
        },
        "rsi": {
            "rsi6": rsi6,
            "rsi12": rsi12,
            "rsi24": rsi24
        },
        "bias": {
            "bias20": bias20,
            "bias60": bias60
        },
        "fibonacci": fibonacci
    }


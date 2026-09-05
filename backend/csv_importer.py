"""
CSV Importer Module for Taiwan Stock Market
Parses user-provided CSV files (TWSE exports, Yahoo Finance, broker formats, generic OHLCV)
Handles traditional Chinese headers, ROC years (民國年), comma formatting, and generates standard candle data.
"""

import io
import csv
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

def parse_date_string(date_str: str) -> Optional[str]:
    """
    Parses various date formats to YYYY-MM-DD:
    - ROC date: 113/05/20, 113-05-20, 113年05月20日
    - Western date: 2024/05/20, 2024-05-20, 20240520
    """
    if not date_str:
        return None
    s = str(date_str).strip().replace("年", "/").replace("月", "/").replace("日", "").replace(".", "/")
    s = s.replace("-", "/")

    parts = s.split("/")
    if len(parts) == 3:
        y, m, d = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if y.isdigit() and m.isdigit() and d.isdigit():
            year_int = int(y)
            # ROC Year handling (e.g. 112 -> 2023, 113 -> 2024)
            if year_int < 1900:
                year_int += 1911
            return f"{year_int:04d}-{int(m):02d}-{int(d):02d}"

    # Check YYYYMMDD
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"

    return None

def clean_number(val: Any) -> Optional[float]:
    """Cleans commas, spaces, currency symbols and converts to float."""
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace("$", "").replace("NT", "").replace("元", "")
    if not s or s == "--" or s == "null" or s == "None":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def parse_csv_content(content: str, filename: str = "custom_stock.csv") -> Dict[str, Any]:
    """
    Parses CSV string content into standard chart data structure with candles and volume.
    """
    lines = content.strip().splitlines()
    if not lines:
        return {"error": "CSV 內容為空"}

    # Find the header line (some files have metadata lines at top)
    reader = csv.reader(lines)
    header_idx = -1
    headers = []
    all_rows = list(reader)

    # Keywords mapping
    date_keys = ["date", "日期", "成交日期", "年月日", "時間", "交易日"]
    open_keys = ["open", "開盤價", "開盤", "買進", "開"]
    high_keys = ["high", "最高價", "最高", "高"]
    low_keys = ["low", "最低價", "最低", "低"]
    close_keys = ["close", "收盤價", "收盤", "成交價", "收", "昨收"]
    vol_keys = ["volume", "成交股數", "成交量", "成交張數", "總量", "股數", "量", "vol"]

    col_map = {}

    for idx, row in enumerate(all_rows[:15]):  # Search within first 15 lines
        row_lower = [c.strip().lower() for c in row]
        found_date = any(k in "".join(row_lower) for k in date_keys)
        found_close = any(k in "".join(row_lower) for k in close_keys)

        if found_date and found_close:
            header_idx = idx
            headers = row_lower
            break

    if header_idx == -1:
        # Fallback: assume first line is header
        headers = [c.strip().lower() for c in all_rows[0]]
        header_idx = 0

    # Map column indices
    for i, h in enumerate(headers):
        clean_h = h.replace(" ", "").replace("_", "")
        if "date" in clean_h or any(k in clean_h for k in date_keys):
            if "date" not in col_map:
                col_map["date"] = i
        elif "open" in clean_h or any(k == clean_h for k in open_keys):
            if "open" not in col_map:
                col_map["open"] = i
        elif "high" in clean_h or any(k == clean_h for k in high_keys):
            if "high" not in col_map:
                col_map["high"] = i
        elif "low" in clean_h or any(k == clean_h for k in low_keys):
            if "low" not in col_map:
                col_map["low"] = i
        elif "close" in clean_h or any(k == clean_h for k in close_keys):
            if "close" not in col_map:
                col_map["close"] = i
        elif "vol" in clean_h or any(k in clean_h for k in vol_keys):
            if "volume" not in col_map:
                col_map["volume"] = i

    # Validate required columns
    if "date" not in col_map or "close" not in col_map:
        return {"error": "CSV 缺少必要欄位 (需包含日期與收盤價欄位)"}

    candles = []
    volume_bars = []

    req_indices = [col_map["date"], col_map["close"]]
    for row in all_rows[header_idx + 1:]:
        if not row or any(idx >= len(row) for idx in req_indices):
            continue

        raw_date = row[col_map["date"]]
        parsed_date = parse_date_string(raw_date)
        if not parsed_date:
            continue

        c_val = clean_number(row[col_map["close"]])
        if c_val is None:
            continue

        o_val = clean_number(row[col_map["open"]]) if "open" in col_map and col_map["open"] < len(row) else c_val
        h_val = clean_number(row[col_map["high"]]) if "high" in col_map and col_map["high"] < len(row) else max(o_val, c_val)
        l_val = clean_number(row[col_map["low"]]) if "low" in col_map and col_map["low"] < len(row) else min(o_val, c_val)
        v_val = clean_number(row[col_map["volume"]]) if "volume" in col_map and col_map["volume"] < len(row) else 0

        # Adjust for possible inverted high/low
        h_val = max(h_val, o_val, c_val)
        l_val = min(l_val, o_val, c_val)
        v_int = int(v_val) if v_val else 0

        candles.append({
            "time": parsed_date,
            "date": parsed_date,
            "open": round(o_val, 2),
            "high": round(h_val, 2),
            "low": round(l_val, 2),
            "close": round(c_val, 2),
            "volume": v_int
        })

        volume_bars.append({
            "time": parsed_date,
            "value": v_int,
            "is_up": c_val >= o_val
        })

    if not candles:
        return {"error": "未能從 CSV 解析出有效的股票交易數據"}

    # Deduplicate by time (keeping latest) and sort ascendingly
    seen_times = {}
    for c, v in zip(candles, volume_bars):
        seen_times[c["time"]] = (c, v)

    sorted_times = sorted(seen_times.keys())
    candles = [seen_times[t][0] for t in sorted_times]
    volume_bars = [seen_times[t][1] for t in sorted_times]

    # Stock Name / Code deduction from filename
    name_part = filename.replace(".csv", "").replace("STOCK_DAY_", "")
    code_match = re.search(r'\d{4}', name_part)
    stock_code = code_match.group(0) if code_match else "CSV"
    stock_name = f"匯入標的 ({name_part})"

    current_price = candles[-1]["close"]
    prev_close = candles[-2]["close"] if len(candles) > 1 else candles[0]["open"]
    change = round(current_price - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0

    summary = {
        "symbol": f"{stock_code}.CSV",
        "code": stock_code,
        "name": stock_name,
        "market": "自訂匯入",
        "industry": "CSV 資料集",
        "currency": "TWD",
        "regularMarketPrice": current_price,
        "previousClose": prev_close,
        "change": change,
        "changePercent": change_pct,
        "high": max(c["high"] for c in candles[-1:]),
        "low": min(c["low"] for c in candles[-1:]),
        "open": candles[-1]["open"],
        "limitUp": round(prev_close * 1.10, 2),
        "limitDown": round(prev_close * 0.90, 2),
        "volumeShares": candles[-1]["volume"],
        "volumeLots": round(candles[-1]["volume"] / 1000, 1),
        "lastUpdate": candles[-1]["date"]
    }

    return {
        "summary": summary,
        "candles": candles,
        "volume": volume_bars,
        "is_intraday": False,
        "interval": "1d",
        "range": "custom_csv"
    }

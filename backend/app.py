"""
FastAPI Main Application for Taiwan Stock Technical Analysis System
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Query, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from tw_stocks import search_stocks, get_stock_info, get_watchlist_categories
from data_fetcher import fetch_stock_chart_data
from indicators import calculate_indicators
from screener import diagnose_stock, run_strategy_screener
from backtest import run_backtest
from csv_importer import parse_csv_content

app = FastAPI(title="Taiwan Stock Technical Analysis System", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global catch-all for unhandled server exceptions with friendly Chinese message"""
    return JSONResponse(
        status_code=500,
        content={"error": f"伺服器處理請求時發生異常: {str(exc)}。請檢查輸入參數或稍後重試。"}
    )

@app.get("/api/search")
def api_search(q: str = Query("", description="Stock code or Chinese name")):
    """Search stocks by code or name"""
    return {"results": search_stocks(q)}

@app.get("/api/categories")
def api_categories():
    """Get popular watchlist category presets"""
    return {"categories": get_watchlist_categories()}

@app.get("/api/stock/{code}")
def api_stock_data(
    code: str,
    interval: str = Query("1d", description="5m, 15m, 60m, 1d, 1wk, 1mo"),
    range: str = Query("1y", description="5d, 1mo, 3mo, 6mo, 1y, 2y, 5y")
):
    """Get candlestick OHLCV, market summary, indicators, and AI diagnosis all in one call"""
    data = fetch_stock_chart_data(code, interval=interval, time_range=range)
    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    candles = data.get("candles", [])
    try:
        indicators = calculate_indicators(candles)
        diag = diagnose_stock(candles, indicators)
        data["indicators"] = indicators
        data["diagnosis"] = diag

        # If this is an ETF, evaluate real-time timing (MACD, MA, Premium/Discount, Spread)
        if data.get("summary", {}).get("etf"):
            from etf_analyzer import evaluate_etf_timing
            etf_data = data["summary"]["etf"]
            timing = evaluate_etf_timing(etf_data, candles, indicators)
            etf_data["timing"] = timing
            data["summary"]["etf"] = etf_data
    except Exception as e:
        data["indicators"] = {}
        data["diagnosis"] = {"score": 50, "rating": "中立整理", "signals": [], "dimensions": {}}
    return data

@app.get("/api/indicators/{code}")
def api_stock_indicators(
    code: str,
    interval: str = Query("1d"),
    range: str = Query("1y")
):
    """Get calculated indicators (MA, BB, KD, MACD, RSI, VMA, BIAS)"""
    data = fetch_stock_chart_data(code, interval=interval, time_range=range)
    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    candles = data.get("candles", [])
    indicators = calculate_indicators(candles)
    return {
        "summary": data.get("summary"),
        "indicators": indicators
    }

@app.get("/api/diagnosis/{code}")
def api_stock_diagnosis(
    code: str,
    interval: str = Query("1d"),
    range: str = Query("1y")
):
    """Get AI technical diagnosis report, radar scores and signals"""
    data = fetch_stock_chart_data(code, interval=interval, time_range=range)
    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    candles = data.get("candles", [])
    indicators = calculate_indicators(candles)
    diag = diagnose_stock(candles, indicators)
    return {
        "summary": data.get("summary"),
        "diagnosis": diag
    }

@app.get("/api/institutional/{code}")
def api_institutional(code: str):
    """Get latest institutional flow and fundamentals for stock"""
    from fundamentals import get_stock_fundamentals, get_institutional_flow
    clean_code = code.split(".")[0].strip()
    fund = get_stock_fundamentals(clean_code)
    inst = get_institutional_flow(clean_code)
    return {
        "code": clean_code,
        "fundamentals": fund,
        "institutional": inst
    }

@app.get("/api/etf/{code}")
def api_etf_analysis(code: str):
    """Get real-time ETF Premium/Discount, Bid-Ask Spread and Technical Timing"""
    from etf_analyzer import get_complete_etf_analysis
    clean_code = code.split(".")[0].strip()
    data = fetch_stock_chart_data(clean_code, interval="1d", time_range="6mo")
    candles = data.get("candles", [])
    indicators = calculate_indicators(candles) if candles else {}
    analysis = get_complete_etf_analysis(clean_code, data.get("summary", {}).get("market", "TWSE"), candles, indicators)
    if not analysis:
        return JSONResponse(status_code=404, content={"error": f"代碼 {code} 不是台股指數股票型基金 (ETF)"})
    return analysis

@app.get("/api/screener/{strategy_id}")
def api_screener(strategy_id: str):
    """Run strategy screener across universe"""
    results = run_strategy_screener(strategy_id)
    return {"strategy": strategy_id, "count": len(results), "matches": results}

@app.get("/api/backtest/{code}")
def api_backtest(
    code: str,
    strategy: str = Query("kd_cross", description="kd_cross, ma_cross, bb_rebound, macd_turn_positive"),
    range: str = Query("2y"),
    stop_loss: float = Query(7.0, description="Stop loss percentage e.g. 7.0"),
    take_profit: float = Query(15.0, description="Take profit percentage e.g. 15.0"),
    include_costs: bool = Query(True, description="Include Taiwan transaction tax and fees")
):
    """Run technical backtest simulation with customizable risk and costs"""
    data = fetch_stock_chart_data(code, interval="1d", time_range=range)
    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    candles = data.get("candles", [])
    indicators = calculate_indicators(candles)
    result = run_backtest(
        candles,
        indicators,
        strategy=strategy,
        stop_loss_pct=stop_loss,
        take_profit_pct=take_profit,
        include_costs=include_costs
    )
    return {
        "summary": data.get("summary"),
        "backtest": result
    }

@app.get("/api/dashboard_summary")
def api_dashboard_summary():
    """
    Returns high-level technical summary for bellwether Taiwan stocks
    focusing explicitly on MA5/MA20/MA60, MACD, and RSI.
    """
    core_stocks = ["2330", "2317", "2454", "0050", "2603", "2382", "3231", "8069"]
    results = []
    bullish_ma_count = 0
    positive_macd_count = 0
    total_rsi = 0.0
    rsi_count = 0

    for code in core_stocks:
        data = fetch_stock_chart_data(code, interval="1d", time_range="6mo", use_cache=True)
        if "error" in data or not data.get("candles"):
            continue

        candles = data["candles"]
        ind = calculate_indicators(candles)
        summary = data["summary"]
        diag = diagnose_stock(candles, ind)

        ma5_val = ind["ma"]["ma5"][-1]["value"] if ind.get("ma", {}).get("ma5") else None
        ma20_val = ind["ma"]["ma20"][-1]["value"] if ind.get("ma", {}).get("ma20") else None
        ma60_val = ind["ma"]["ma60"][-1]["value"] if ind.get("ma", {}).get("ma60") else None

        # MA Alignment status
        ma_status = "neutral"
        ma_label = "均線糾結"
        if ma5_val and ma20_val and ma60_val:
            if ma5_val > ma20_val > ma60_val:
                ma_status = "bullish"
                ma_label = "多頭排列 (MA5 > MA20 > MA60)"
                bullish_ma_count += 1
            elif ma5_val < ma20_val < ma60_val:
                ma_status = "bearish"
                ma_label = "空頭排列 (MA5 < MA20 < MA60)"
            elif summary["regularMarketPrice"] > ma20_val:
                ma_status = "above_ma20"
                ma_label = "站上月線 (Price > MA20)"

        # MACD status
        macd_bar = ind.get("macd", {}).get("bar", [])
        macd_val = macd_bar[-1]["value"] if macd_bar else 0.0
        macd_prev = macd_bar[-2]["value"] if len(macd_bar) > 1 else 0.0
        macd_status = "red_expand" if macd_val > 0 and macd_val >= macd_prev else ("red_contract" if macd_val > 0 else ("green_contract" if macd_val > macd_prev else "green_expand"))
        if macd_val > 0:
            positive_macd_count += 1

        # RSI status
        rsi6_list = ind.get("rsi", {}).get("rsi6", [])
        rsi6_val = rsi6_list[-1]["value"] if rsi6_list else 50.0
        total_rsi += rsi6_val
        rsi_count += 1

        results.append({
            "code": summary["code"],
            "name": summary["name"],
            "market": summary["market"],
            "industry": summary["industry"],
            "price": summary["regularMarketPrice"],
            "change": summary["change"],
            "changePercent": summary["changePercent"],
            "volumeLots": summary["volumeLots"],
            "ma": {
                "ma5": ma5_val,
                "ma20": ma20_val,
                "ma60": ma60_val,
                "status": ma_status,
                "label": ma_label
            },
            "macd": {
                "bar": macd_val,
                "isPositive": macd_val > 0,
                "status": macd_status,
                "dif": (ind.get("macd", {}).get("dif") or [{}])[-1].get("value", 0.0),
                "dea": (ind.get("macd", {}).get("dea") or [{}])[-1].get("value", 0.0)
            },
            "rsi": {
                "rsi6": rsi6_val,
                "status": "overbought" if rsi6_val > 75 else ("oversold" if rsi6_val < 25 else "neutral")
            },
            "score": diag.get("score", 50),
            "rating": diag.get("rating", "中立整理")
        })

    # Market Temperature: 0 to 100
    valid_count = len(results) or 1
    avg_rsi = total_rsi / rsi_count if rsi_count else 50.0
    ma_pct = (bullish_ma_count / valid_count) * 100
    macd_pct = (positive_macd_count / valid_count) * 100
    market_temp = round(ma_pct * 0.4 + macd_pct * 0.4 + avg_rsi * 0.2, 1)

    return {
        "marketTemperature": market_temp,
        "marketMood": "強勢多頭" if market_temp >= 70 else ("偏多震盪" if market_temp >= 55 else ("中立整理" if market_temp >= 40 else "偏空保守")),
        "bullishMaRatio": round(ma_pct, 1),
        "positiveMacdRatio": round(macd_pct, 1),
        "averageRsi": round(avg_rsi, 1),
        "stocks": results
    }

@app.get("/api/etf_dashboard")
def api_etf_dashboard(codes: str = None):
    """
    Returns real-time technical & fundamental metrics for custom/hot ETFs:
    MA5/MA20/MA60 alignment, MACD momentum, KD (9,3,3) cross & status,
    RSI (6) level, real-time Net Asset Value (NAV), and Premium/Discount.
    """
    default_hot_etfs = [
        "0050", "0056", "00878", "00919", "00929", "006208",
        "00713", "00940", "00679B", "00687B", "00937B", "00757"
    ]

    if isinstance(codes, str) and codes.strip():
        etf_codes = [c.strip().upper() for c in codes.split(",") if c.strip()]
    else:
        etf_codes = default_hot_etfs

    from etf_analyzer import fetch_all_etf_map, evaluate_etf_timing
    all_etf_map = fetch_all_etf_map()

    results = []
    bullish_ma_count = 0
    positive_macd_count = 0
    bullish_kd_count = 0
    discount_count = 0
    total_rsi = 0.0
    rsi_count = 0
    total_prem_disc = 0.0
    prem_disc_count = 0

    for code in etf_codes:
        clean_code = code.split(".")[0].strip()
        data = fetch_stock_chart_data(clean_code, interval="1d", time_range="6mo", use_cache=True)
        if "error" in data or not data.get("candles"):
            continue

        candles = data["candles"]
        ind = calculate_indicators(candles)
        summary = data["summary"]
        diag = diagnose_stock(candles, ind)

        # Real-time ETF info from MIS (NAV, Premium/Discount, Units)
        etf_mis = all_etf_map.get(clean_code, {})
        nav = etf_mis.get("nav", 0.0)
        prev_nav = etf_mis.get("prevNav", 0.0)
        market_price = summary.get("regularMarketPrice", 0.0)

        # If MIS has real-time marketPrice, prioritize it if valid
        if etf_mis.get("marketPrice") and etf_mis["marketPrice"] > 0:
            mis_market_price = etf_mis["marketPrice"]
        else:
            mis_market_price = market_price

        effective_nav = nav if nav > 0 else prev_nav

        diff = etf_mis.get("diff", 0.0)
        prem_disc_pct = etf_mis.get("premiumDiscountPercent", 0.0)
        if effective_nav > 0 and (diff == 0.0 or prem_disc_pct == 0.0) and mis_market_price > 0:
            diff = round(mis_market_price - effective_nav, 2)
            prem_disc_pct = round((diff / effective_nav) * 100, 2)

        # Premium / Discount Status evaluation
        if prem_disc_pct < -0.4:
            prem_status = "deep_discount"
            prem_label = f"大幅折價 ({prem_disc_pct}%)"
            discount_count += 1
        elif prem_disc_pct < -0.1:
            prem_status = "mild_discount"
            prem_label = f"輕微折價 ({prem_disc_pct}%)"
            discount_count += 1
        elif prem_disc_pct <= 0.3:
            prem_status = "fair"
            prem_label = f"合理區間 ({'+' if prem_disc_pct > 0 else ''}{prem_disc_pct}%)"
        elif prem_disc_pct <= 0.8:
            prem_status = "mild_premium"
            prem_label = f"偏高溢價 (+{prem_disc_pct}%)"
        else:
            prem_status = "danger_premium"
            prem_label = f"⚠️ 嚴重溢價 (+{prem_disc_pct}%)"

        if effective_nav > 0:
            total_prem_disc += prem_disc_pct
            prem_disc_count += 1

        # 1. Moving Averages (MA5, MA20, MA60)
        ma5_val = ind.get("ma", {}).get("ma5", [{}])[-1].get("value") if ind.get("ma", {}).get("ma5") else None
        ma20_val = ind.get("ma", {}).get("ma20", [{}])[-1].get("value") if ind.get("ma", {}).get("ma20") else None
        ma60_val = ind.get("ma", {}).get("ma60", [{}])[-1].get("value") if ind.get("ma", {}).get("ma60") else None

        ma_status = "neutral"
        ma_label = "均線糾結"
        if ma5_val and ma20_val and ma60_val:
            if ma5_val > ma20_val > ma60_val:
                ma_status = "bullish"
                ma_label = "多頭排列 (MA5 > MA20 > MA60)"
                bullish_ma_count += 1
            elif ma5_val < ma20_val < ma60_val:
                ma_status = "bearish"
                ma_label = "空頭排列 (MA5 < MA20 < MA60)"
            elif summary["regularMarketPrice"] > ma20_val:
                ma_status = "above_ma20"
                ma_label = "站上月線 (Price > MA20)"
        elif ma5_val and ma20_val:
            if ma5_val > ma20_val:
                ma_status = "bullish"
                ma_label = "短期偏多 (MA5 > MA20)"
            elif ma5_val < ma20_val:
                ma_status = "bearish"
                ma_label = "短期偏空 (MA5 < MA20)"

        # 2. MACD (12, 26, 9)
        macd_bar = ind.get("macd", {}).get("bar", [])
        macd_val = macd_bar[-1]["value"] if macd_bar else 0.0
        macd_prev = macd_bar[-2]["value"] if len(macd_bar) > 1 else 0.0
        macd_status = (
            "red_expand" if macd_val > 0 and macd_val >= macd_prev
            else ("red_contract" if macd_val > 0
            else ("green_contract" if macd_val > macd_prev
            else "green_expand"))
        )
        if macd_val > 0:
            positive_macd_count += 1

        # 3. KD (9, 3, 3)
        kd_k_list = ind.get("kd", {}).get("k", [])
        kd_d_list = ind.get("kd", {}).get("d", [])
        k_val = kd_k_list[-1]["value"] if kd_k_list else 50.0
        d_val = kd_d_list[-1]["value"] if kd_d_list else 50.0
        prev_k = kd_k_list[-2]["value"] if len(kd_k_list) > 1 else k_val
        prev_d = kd_d_list[-2]["value"] if len(kd_d_list) > 1 else d_val

        if prev_k <= prev_d and k_val > d_val:
            kd_cross = "golden_cross"
            kd_cross_label = "🔥 黃金交叉 (K穿D)"
            kd_is_bullish = True
        elif prev_k >= prev_d and k_val < d_val:
            kd_cross = "death_cross"
            kd_cross_label = "⚠️ 死亡交叉 (K破D)"
            kd_is_bullish = False
        elif k_val > d_val:
            kd_cross = "k_above_d"
            kd_cross_label = "多方佔優 (K > D)"
            kd_is_bullish = True
        else:
            kd_cross = "k_below_d"
            kd_cross_label = "空方偏弱 (K < D)"
            kd_is_bullish = False

        if kd_is_bullish:
            bullish_kd_count += 1

        if k_val >= 80 and d_val >= 80:
            kd_zone = "overbought"
            kd_zone_label = "高檔超買 (>80)"
        elif k_val <= 20 and d_val <= 20:
            kd_zone = "oversold"
            kd_zone_label = "低檔超賣 (<20)"
        else:
            kd_zone = "neutral"
            kd_zone_label = "常態整理區"

        # 4. RSI (6, 12)
        rsi6_list = ind.get("rsi", {}).get("rsi6", [])
        rsi12_list = ind.get("rsi", {}).get("rsi12", [])
        rsi6_val = rsi6_list[-1]["value"] if rsi6_list else 50.0
        rsi12_val = rsi12_list[-1]["value"] if rsi12_list else 50.0
        total_rsi += rsi6_val
        rsi_count += 1

        rsi_status = "overbought" if rsi6_val > 75 else ("oversold" if rsi6_val < 25 else ("bull_zone" if rsi6_val >= 55 else "neutral"))

        # 5. Timing evaluation combining ETF factors
        merged_etf_info = {
            "code": clean_code,
            "name": summary["name"],
            "marketPrice": mis_market_price,
            "nav": effective_nav,
            "prevNav": prev_nav,
            "diff": diff,
            "premiumDiscountPercent": prem_disc_pct,
            "spreadPercent": etf_mis.get("spreadPercent", 0.05)
        }
        timing = evaluate_etf_timing(merged_etf_info, candles, ind)

        results.append({
            "code": summary["code"],
            "name": summary["name"],
            "market": summary["market"],
            "industry": summary["industry"],
            "price": summary["regularMarketPrice"],
            "change": summary["change"],
            "changePercent": summary["changePercent"],
            "volumeLots": summary["volumeLots"],
            "etf": {
                "nav": effective_nav,
                "prevNav": prev_nav,
                "diff": diff,
                "premiumDiscountPercent": prem_disc_pct,
                "issuedUnits": etf_mis.get("issuedUnits", ""),
                "diffUnits": etf_mis.get("diffUnits", ""),
                "refUrl": etf_mis.get("refUrl", ""),
                "status": prem_status,
                "label": prem_label,
                "date": etf_mis.get("date", ""),
                "time": etf_mis.get("time", "")
            },
            "ma": {
                "ma5": ma5_val,
                "ma20": ma20_val,
                "ma60": ma60_val,
                "status": ma_status,
                "label": ma_label
            },
            "macd": {
                "bar": macd_val,
                "isPositive": macd_val > 0,
                "status": macd_status,
                "dif": (ind.get("macd", {}).get("dif") or [{}])[-1].get("value", 0.0),
                "dea": (ind.get("macd", {}).get("dea") or [{}])[-1].get("value", 0.0)
            },
            "kd": {
                "k": k_val,
                "d": d_val,
                "cross": kd_cross,
                "crossLabel": kd_cross_label,
                "zone": kd_zone,
                "zoneLabel": kd_zone_label,
                "isBullish": kd_is_bullish
            },
            "rsi": {
                "rsi6": rsi6_val,
                "rsi12": rsi12_val,
                "status": rsi_status
            },
            "timing": timing,
            "score": timing.get("score", diag.get("score", 50)),
            "action": timing.get("action", diag.get("rating", "中立整理")),
            "actionColor": timing.get("actionColor", "#b0bec5")
        })

    valid_count = len(results) or 1
    avg_rsi = round(total_rsi / rsi_count, 1) if rsi_count else 50.0
    avg_prem = round(total_prem_disc / prem_disc_count, 2) if prem_disc_count else 0.0
    ma_pct = round((bullish_ma_count / valid_count) * 100, 1)
    macd_pct = round((positive_macd_count / valid_count) * 100, 1)
    kd_pct = round((bullish_kd_count / valid_count) * 100, 1)

    return {
        "etfCount": len(results),
        "bullishMaRatio": ma_pct,
        "positiveMacdRatio": macd_pct,
        "bullishKdRatio": kd_pct,
        "averageRsi": avg_rsi,
        "averagePremiumDiscount": avg_prem,
        "discountCount": discount_count,
        "etfs": results
    }

@app.post("/api/upload_csv")
async def api_upload_csv(file: UploadFile = File(...)):
    """Upload and parse custom CSV file"""
    try:
        content_bytes = await file.read()
        try:
            content_str = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_str = content_bytes.decode("cp950", errors="ignore")

        data = parse_csv_content(content_str, filename=file.filename or "custom_stock.csv")
        if "error" in data:
            return JSONResponse(status_code=400, content=data)

        candles = data.get("candles", [])
        indicators = calculate_indicators(candles)
        diag = diagnose_stock(candles, indicators)

        return {
            "chartData": data,
            "indicators": indicators,
            "diagnosis": diag
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"CSV 解析失敗: {str(e)}"})

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/favicon.ico")
def serve_favicon():
    svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0b0e14"/><path d="M12 44 L24 30 L36 38 L52 18" fill="none" stroke="#00b4d8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="52" cy="18" r="4" fill="#ff4d4f"/></svg>"""
    return Response(content=svg_icon, media_type="image/svg+xml")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Taiwan Stock Technical Analysis System API is running. Index file pending."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

"""
Comprehensive Automated Test Suite for Taiwan Stock Technical Analysis System
Validates Search, Data Fetching, Indicators, Screener, Backtesting, Dashboard, and CSV Import.
"""

import sys
import os
import io
import json
import unittest

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tw_stocks import search_stocks, get_stock_info, get_watchlist_categories
from data_fetcher import fetch_stock_chart_data
from indicators import calculate_indicators
from screener import diagnose_stock, run_strategy_screener
from backtest import run_backtest
from csv_importer import parse_csv_content, parse_date_string

class TestTaiwanStockSystem(unittest.TestCase):

    def test_01_stock_search_and_two_suffix_fix(self):
        """Verify stock search, fuzzy Chinese search, and .TWO suffix bug fix."""
        # 1. Exact code
        r1 = search_stocks("2330")
        self.assertTrue(any(s["code"] == "2330" for s in r1), "Search 2330 failed")
        
        # 2. Chinese name
        r2 = search_stocks("台積電")
        self.assertTrue(any("台積電" in s["name"] for s in r2), "Search 台積電 failed")

        # 3. .TWO suffix bug verification (Previously failed due to .TWO -> .O bug)
        r3 = search_stocks("8069.TWO")
        self.assertTrue(len(r3) > 0, "Search 8069.TWO returned empty results")
        self.assertEqual(r3[0]["code"], "8069", "8069.TWO did not map to 8069")
        self.assertEqual(r3[0]["market"], "TPEx", "8069 should be TPEx")

        # 4. .TW suffix
        r4 = search_stocks("2317.TW")
        self.assertTrue(any(s["code"] == "2317" for s in r4), "Search 2317.TW failed")

        # 5. Fuzzy Chinese match (e.g. 玉山金, 長榮, 聯發科)
        r5 = search_stocks("玉山")
        self.assertTrue(any(s["code"] == "2884" for s in r5), "Search 玉山 failed")

    def test_02_data_fetcher_daily_and_intraday(self):
        """Verify data fetching for TWSE, TPEx, Daily, and Intraday 5m with deduplication."""
        # 1. TWSE Daily
        d1 = fetch_stock_chart_data("2330", interval="1d", time_range="1mo")
        self.assertNotIn("error", d1, f"Failed to fetch 2330.TW: {d1.get('error')}")
        self.assertGreater(len(d1["candles"]), 10, "Candles count should be > 10")
        
        # Check summary fields
        s1 = d1["summary"]
        self.assertEqual(s1["code"], "2330")
        self.assertGreater(s1["regularMarketPrice"], 0)
        self.assertLess(s1["limitDown"], s1["regularMarketPrice"])

        # Test 1y range (previously buggy due to chartPreviousClose taking 1y ago price)
        d1y = fetch_stock_chart_data("2330", interval="1d", time_range="1y", use_cache=False)
        s1y = d1y["summary"]
        self.assertLessEqual(abs(s1y["changePercent"]), 10.5, f"Daily change percent {s1y['changePercent']}% exceeded Taiwan 10% limit")
        self.assertGreaterEqual(s1y["limitUp"], s1y["regularMarketPrice"])
        self.assertLessEqual(s1y["limitDown"], s1y["regularMarketPrice"])
        self.assertAlmostEqual(s1y["change"], s1y["regularMarketPrice"] - s1y["previousClose"], delta=0.05)

        # Check timestamp ordering and uniqueness (Our deduplication fix)
        times = [c["time"] for c in d1["candles"]]
        self.assertEqual(times, sorted(list(set(times))), "Candle times must be strictly ascending and unique")

        # 2. TPEx OTC Stock (8069.TWO)
        d2 = fetch_stock_chart_data("8069", interval="1d", time_range="1mo")
        self.assertNotIn("error", d2, f"Failed to fetch 8069.TWO: {d2.get('error')}")
        self.assertEqual(d2["summary"]["market"], "TPEx")

        # 3. Intraday 5m (High/Low fix verification)
        d3 = fetch_stock_chart_data("2330", interval="5m", time_range="5d")
        self.assertNotIn("error", d3, f"Failed to fetch 2330 5m: {d3.get('error')}")
        s3 = d3["summary"]
        self.assertGreaterEqual(s3["high"], s3["low"], "Intraday high must be >= low")
        self.assertGreater(s3["high"], 0, "Intraday day high must be > 0")

    def test_03_technical_indicators_calculation(self):
        """Verify calculation of MA5/20/60, KD, MACD, RSI, Bollinger, BIAS."""
        d = fetch_stock_chart_data("2330", interval="1d", time_range="6mo")
        candles = d["candles"]
        ind = calculate_indicators(candles)

        # 1. Moving Averages
        ma = ind.get("ma", {})
        self.assertIn("ma5", ma)
        self.assertIn("ma20", ma)
        self.assertIn("ma60", ma)
        self.assertGreater(len(ma["ma5"]), 0, "MA5 should have data")
        self.assertGreater(len(ma["ma20"]), 0, "MA20 should have data")
        self.assertGreater(len(ma["ma60"]), 0, "MA60 should have data")

        # 2. KD (9, 3, 3)
        kd = ind.get("kd", {})
        self.assertIn("k", kd)
        self.assertIn("d", kd)
        self.assertGreater(len(kd["k"]), 0, "K values should exist")
        # K and D should be bounded roughly between 0 and 100
        latest_k = kd["k"][-1]["value"]
        self.assertTrue(0 <= latest_k <= 100, f"K value {latest_k} out of range [0, 100]")

        # 3. MACD (12, 26, 9)
        macd = ind.get("macd", {})
        self.assertIn("dif", macd)
        self.assertIn("dea", macd)
        self.assertIn("bar", macd)
        self.assertGreater(len(macd["dif"]), 0)
        self.assertGreater(len(macd["bar"]), 0)

        # 4. RSI (6, 12, 24)
        rsi = ind.get("rsi", {})
        self.assertIn("rsi6", rsi)
        self.assertIn("rsi12", rsi)
        self.assertGreater(len(rsi["rsi6"]), 0)
        latest_rsi6 = rsi["rsi6"][-1]["value"]
        self.assertTrue(0 <= latest_rsi6 <= 100, f"RSI6 value {latest_rsi6} out of range [0, 100]")

        # 5. Bollinger Bands (20, 2)
        bb = ind.get("bollinger", {})
        self.assertIn("upper", bb)
        self.assertIn("middle", bb)
        self.assertIn("lower", bb)
        self.assertGreater(len(bb["upper"]), 0)
        self.assertGreater(bb["upper"][-1]["value"], bb["lower"][-1]["value"], "BB upper must be > lower")

        # 6. BIAS (20, 60)
        bias = ind.get("bias", {})
        self.assertIn("bias20", bias)
        self.assertIn("bias60", bias)
        self.assertGreater(len(bias["bias20"]), 0, "BIAS20 should have data")

        # 7. Fibonacci Retracement & Support/Resistance
        fib = ind.get("fibonacci", {})
        self.assertIn("swingHigh", fib)
        self.assertIn("swingLow", fib)
        self.assertIn("levels", fib)
        self.assertGreater(fib["swingHigh"], fib["swingLow"], "Swing high must be > swing low")
        self.assertEqual(len(fib["levels"]), 7, "Should have 7 Fibonacci levels")
        self.assertGreater(len(bias["bias60"]), 0, "BIAS60 should have data")

    def test_04_diagnosis_and_screener(self):
        """Verify AI technical diagnosis radar and multi-stock screener execution."""
        d = fetch_stock_chart_data("2330", interval="1d", time_range="6mo")
        candles = d["candles"]
        ind = calculate_indicators(candles)
        diag = diagnose_stock(candles, ind)

        self.assertIn("score", diag)
        self.assertTrue(0 <= diag["score"] <= 100, f"Score {diag['score']} out of [0, 100]")
        self.assertIn("rating", diag)
        self.assertIn("dimensions", diag)
        self.assertIn("signals", diag)

        # Run Screener strategies (verifying no IndexError)
        for strategy in ["kd_golden_cross", "ma_bullish_breakout", "bb_lower_rebound", "macd_turn_positive", "volume_breakout"]:
            matches = run_strategy_screener(strategy)
            self.assertIsInstance(matches, list, f"Screener strategy {strategy} did not return a list")

    def test_05_backtest_simulation(self):
        """Verify backtesting engine for KD cross, MA cross, Bollinger rebound, MACD, custom stop-loss/take-profit, and equity curve."""
        d = fetch_stock_chart_data("2330", interval="1d", time_range="2y")
        candles = d["candles"]
        ind = calculate_indicators(candles)
        
        # 1. KD cross with custom stop loss, take profit and transaction costs
        bt_kd = run_backtest(candles, ind, strategy="kd_cross", stop_loss_pct=5.0, take_profit_pct=12.0, include_costs=True)
        self.assertIn("strategyReturn", bt_kd)
        self.assertIn("winRate", bt_kd)
        self.assertIn("totalTrades", bt_kd)
        self.assertIn("maxDrawdown", bt_kd)
        self.assertIn("profitFactor", bt_kd)
        self.assertIn("equityCurve", bt_kd)
        self.assertIn("markers", bt_kd)
        self.assertIsInstance(bt_kd["trades"], list)
        self.assertGreater(len(bt_kd["equityCurve"]), 10, "Equity curve points should exist")

        # 2. MA cross
        bt_ma = run_backtest(candles, ind, strategy="ma_cross")
        self.assertIn("strategyReturn", bt_ma)
        self.assertIn("winRate", bt_ma)

        # 3. Bollinger rebound
        bt_bb = run_backtest(candles, ind, strategy="bb_rebound")
        self.assertIn("strategyReturn", bt_bb)
        self.assertIn("winRate", bt_bb)

        # 4. MACD turn positive
        bt_macd = run_backtest(candles, ind, strategy="macd_turn_positive")
        self.assertIn("strategyReturn", bt_macd)
        self.assertIn("winRate", bt_macd)

    def test_06_csv_importer_and_roc_dates(self):
        """Verify CSV parsing with ROC years, Chinese headers, and deduplication."""
        sample_csv = """
日期,成交股數,開盤價,最高價,最低價,收盤價,成交金額
113/08/01,10000000,950.00,960.00,945.00,958.00,9500000000
113/08/02,12000000,955.00,965.00,950.00,960.00,11500000000
113/08/05,15000000,960.00,970.00,955.00,968.00,14500000000
113/08/05,15000000,960.00,970.00,955.00,968.00,14500000000
113/08/06,11000000,968.00,980.00,965.00,975.00,10700000000
        """
        # Note: 113/08/05 has a duplicate row to test our deduplication fix!
        parsed = parse_csv_content(sample_csv, filename="test_2330.csv")
        self.assertNotIn("error", parsed, f"CSV parsing failed: {parsed.get('error')}")
        
        candles = parsed["candles"]
        # Should have 4 unique dates (113/08/01 -> 2024-08-01, 02, 05, 06)
        self.assertEqual(len(candles), 4, "Duplicate date 113/08/05 was not deduplicated")
        self.assertEqual(candles[0]["time"], "2024-08-01", "ROC year 113 should convert to 2024")
        self.assertEqual(candles[-1]["time"], "2024-08-06")

        # Test Western format date
        self.assertEqual(parse_date_string("2024-05-20"), "2024-05-20")
        self.assertEqual(parse_date_string("112/10/15"), "2023-10-15")

    def test_07_dashboard_summary_and_empty_list_safety(self):
        """Verify /api/dashboard_summary logic and check dif/dea empty list safety."""
        from app import api_dashboard_summary
        dash = api_dashboard_summary()
        self.assertIn("marketTemperature", dash)
        self.assertIn("marketMood", dash)
        self.assertIn("stocks", dash)
        self.assertGreater(len(dash["stocks"]), 0, "Dashboard stocks should not be empty")

        for s in dash["stocks"]:
            self.assertIn("code", s)
            self.assertIn("name", s)
            self.assertIn("ma", s)
            self.assertIn("macd", s)
            self.assertIn("rsi", s)
            # Verify MA5/20/60
            self.assertIn("ma5", s["ma"])
            self.assertIn("ma20", s["ma"])
            self.assertIn("ma60", s["ma"])
            # Verify MACD DIF and DEA numbers
            self.assertIsInstance(s["macd"]["dif"], (int, float))
            self.assertIsInstance(s["macd"]["dea"], (int, float))
            # Verify RSI(6)
            self.assertIsInstance(s["rsi"]["rsi6"], (int, float))

    def test_08_fundamentals_and_institutional_flow(self):
        """Verify TWSE/TPEx PE, PB, Yield fetching and Institutional flow logic."""
        from fundamentals import get_stock_fundamentals, get_institutional_flow, get_simulated_historical_institutional_flow
        from data_fetcher import fetch_stock_chart_data

        # 1. TWSE Stock (2330)
        twse_fund = get_stock_fundamentals("2330")
        self.assertIn("peRatio", twse_fund)
        self.assertIn("pbRatio", twse_fund)
        self.assertIn("dividendYield", twse_fund)
        self.assertGreater(twse_fund["peRatio"], 0, "2330 PE should be greater than 0")
        self.assertGreater(twse_fund["dividendYield"], 0, "2330 Dividend Yield should be greater than 0")

        # 2. TPEx Stock (8069)
        tpex_fund = get_stock_fundamentals("8069")
        self.assertIn("peRatio", tpex_fund)
        self.assertIn("pbRatio", tpex_fund)

        # 3. Institutional daily flow
        inst = get_institutional_flow("2330")
        self.assertIn("foreignLots", inst)
        self.assertIn("trustLots", inst)
        self.assertIn("dealerLots", inst)
        self.assertIn("totalLots", inst)
        self.assertIn("trustConsecutiveDays", inst)
        self.assertIn("isTrustFocus", inst)

        # 4. Full chart data integration check
        chart_data = fetch_stock_chart_data("2330", time_range="6mo")
        summary = chart_data.get("summary", {})
        self.assertIn("peRatio", summary)
        self.assertIn("pbRatio", summary)
        self.assertIn("dividendYield", summary)
        self.assertIn("institutional", summary)
        self.assertIn("institutional", chart_data, "Institutional series should be in chart payload")
        self.assertIn("dividends", chart_data, "Dividends list should be in chart payload")
        self.assertGreater(len(chart_data["institutional"]), 10, "Institutional series points should exist")
        print(f"\n[Test 08 Passed] 2330 PE: {summary['peRatio']}, PB: {summary['pbRatio']}, Yield: {summary['dividendYield']}%, Inst Total: {summary['institutional']['totalLots']}張, Trust Consecutive: {summary['institutional']['trustConsecutiveDays']}天, Dividends count: {len(chart_data['dividends'])}")

    def test_09_single_payload_and_offline_fallback(self):
        """Verify unified single stock payload and offline fallback generation."""
        from data_fetcher import generate_offline_fallback_data
        from app import api_stock_data

        # 1. Test offline fallback generator
        fallback = generate_offline_fallback_data("2330", interval="1d", time_range="1y")
        self.assertIn("candles", fallback)
        self.assertGreater(len(fallback["candles"]), 20)
        self.assertIn("summary", fallback)
        self.assertTrue(fallback["summary"]["isFallback"])
        self.assertIn("institutional", fallback)

        # 2. Test api_stock_data unified response (contains candles, indicators, diagnosis)
        resp = api_stock_data("2330", interval="1d", range="1mo")
        self.assertIn("candles", resp)
        self.assertIn("indicators", resp)
        self.assertIn("diagnosis", resp)
        self.assertIn("ma", resp["indicators"])
        self.assertIn("score", resp["diagnosis"])
        print(f"\n[Test 09 Passed] Unified Payload: Candles={len(resp['candles'])}, Indicators={list(resp['indicators'].keys())}, Score={resp['diagnosis']['score']}")

    def test_10_etf_timing_and_premium_discount(self):
        """Verify ETF Premium/Discount, Bid-Ask Spread and Technical Timing decision matrix."""
        from etf_analyzer import get_complete_etf_analysis, is_etf_code, evaluate_etf_timing
        from app import api_stock_data, api_etf_analysis

        # 1. ETF code detection
        self.assertTrue(is_etf_code("0050"))
        self.assertTrue(is_etf_code("00878"))
        self.assertTrue(is_etf_code("00940"))
        self.assertFalse(is_etf_code("2330"))

        # 2. Complete ETF Analysis for 0050
        etf_0050 = get_complete_etf_analysis("0050", market="TWSE")
        self.assertIsNotNone(etf_0050, "0050 ETF analysis should not be None")
        self.assertIn("nav", etf_0050)
        self.assertIn("marketPrice", etf_0050)
        self.assertIn("premiumDiscountPercent", etf_0050)
        self.assertIn("spread", etf_0050)
        self.assertIn("spreadPercent", etf_0050)
        self.assertIn("liquidityLevel", etf_0050)
        self.assertGreater(etf_0050["marketPrice"], 0, "0050 Market Price should be > 0")

        # 3. Integration with api_stock_data
        resp = api_stock_data("0050", interval="1d", range="6mo")
        summary = resp.get("summary", {})
        self.assertIn("etf", summary, "ETF key should be present in 0050 summary")
        etf_data = summary["etf"]
        self.assertIsNotNone(etf_data)
        self.assertIn("timing", etf_data)
        timing = etf_data["timing"]
        self.assertIn("action", timing)
        self.assertIn("actionColor", timing)
        self.assertIn("reasons", timing)
        self.assertIn("premiumStatus", timing)
        self.assertGreater(len(timing["reasons"]), 0)

        # 5. ETF Chinese Name verification
        from tw_stocks import get_stock_info, search_stocks
        info_00403 = get_stock_info("00403A")
        info_00405 = get_stock_info("00405A")
        self.assertEqual(info_00403["name"], "主動統一升級50", f"00403A name expected '主動統一升級50', got {info_00403['name']}")
        self.assertEqual(info_00405["name"], "主動富邦台灣龍耀", f"00405A name expected '主動富邦台灣龍耀', got {info_00405['name']}")
        
        # Search by code
        search_00405 = search_stocks("00405")
        self.assertTrue(any(s["code"] == "00405A" and s["name"] == "主動富邦台灣龍耀" for s in search_00405))
        
        # Search by keyword
        search_kw = search_stocks("統一升級")
        self.assertTrue(any(s["code"] == "00403A" for s in search_kw))
        
        search_alias = search_stocks("富邦台灣龍耀")
        self.assertTrue(any(s["code"] == "00405A" for s in search_alias))
        
        print(f"[Test 10 Passed] 00403A -> {info_00403['name']}, 00405A -> {info_00405['name']}")

    def test_11_etf_dashboard_api(self):
        """Verify custom ETF dashboard API for MA5/MA20/MA60, MACD, KD, RSI, NAV, and Premium/Discount."""
        from app import api_etf_dashboard
        
        # Test with default hot ETFs
        res = api_etf_dashboard()
        self.assertIn("etfs", res)
        self.assertIn("bullishMaRatio", res)
        self.assertIn("positiveMacdRatio", res)
        self.assertIn("bullishKdRatio", res)
        self.assertIn("averageRsi", res)
        self.assertIn("averagePremiumDiscount", res)
        self.assertGreater(res["etfCount"], 0, "ETF count should be greater than 0")

        # Test with specific custom codes
        custom_res = api_etf_dashboard(codes="0050,0056,00878")
        self.assertEqual(custom_res["etfCount"], 3)
        codes = [item["code"] for item in custom_res["etfs"]]
        self.assertIn("0050", codes)
        self.assertIn("0056", codes)
        self.assertIn("00878", codes)

        first_etf = custom_res["etfs"][0]
        # Check MA
        self.assertIn("ma", first_etf)
        self.assertIn("ma5", first_etf["ma"])
        self.assertIn("ma20", first_etf["ma"])
        self.assertIn("ma60", first_etf["ma"])
        self.assertIn("status", first_etf["ma"])
        self.assertIn("label", first_etf["ma"])

        # Check MACD
        self.assertIn("macd", first_etf)
        self.assertIn("bar", first_etf["macd"])
        self.assertIn("status", first_etf["macd"])
        self.assertIn("dif", first_etf["macd"])
        self.assertIn("dea", first_etf["macd"])

        # Check KD
        self.assertIn("kd", first_etf)
        self.assertIn("k", first_etf["kd"])
        self.assertIn("d", first_etf["kd"])
        self.assertIn("cross", first_etf["kd"])
        self.assertIn("crossLabel", first_etf["kd"])
        self.assertIn("zone", first_etf["kd"])

        # Check RSI
        self.assertIn("rsi", first_etf)
        self.assertIn("rsi6", first_etf["rsi"])

        # Check ETF NAV & Premium/Discount & Units
        self.assertIn("etf", first_etf)
        self.assertIn("nav", first_etf["etf"])
        self.assertIn("prevNav", first_etf["etf"])
        self.assertIn("issuedUnits", first_etf["etf"])
        self.assertIn("diffUnits", first_etf["etf"])
        self.assertIn("refUrl", first_etf["etf"])
        self.assertIn("premiumDiscountPercent", first_etf["etf"])
        self.assertIn("status", first_etf["etf"])
        self.assertIn("label", first_etf["etf"])
        self.assertGreater(first_etf["etf"]["nav"], 0, "ETF NAV should be positive")

        print(f"[Test 11 Passed] Custom ETF dashboard API successfully validated with {custom_res['etfCount']} ETFs. NAV: {first_etf['etf']['nav']}, Prem: {first_etf['etf']['premiumDiscountPercent']}%, Units: {first_etf['etf']['issuedUnits']}")

if __name__ == "__main__":
    unittest.main()


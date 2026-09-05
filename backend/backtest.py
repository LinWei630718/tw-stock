"""
Fast Technical Strategy Backtesting Engine for Taiwan Stock Market
Simulates technical trading rules with customizable stop-loss, take-profit,
Taiwan transaction costs (fees & tax), equity curve, and chart trade markers.
"""

from typing import List, Dict, Any

def run_backtest(
    candles: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    strategy: str = "kd_cross",
    stop_loss_pct: float = 7.0,
    take_profit_pct: float = 15.0,
    include_costs: bool = True
) -> Dict[str, Any]:
    """
    Run backtest simulation.
    Strategies:
    - 'kd_cross': Buy when K crosses above D (<40), Sell on take-profit/stop-loss or K death cross (>65)
    - 'ma_cross': Buy when MA5 crosses above MA20, Sell on take-profit/stop-loss or MA5 death cross MA20
    - 'bb_rebound': Buy when Price touches Lower BB and bounces, Sell on Upper BB or take-profit/stop-loss
    - 'macd_turn_positive': Buy when MACD OSC turns positive, Sell on OSC turn negative or take-profit/stop-loss
    """
    if not candles or len(candles) < 30:
        return {"error": "歷史資料量不足以執行回測"}

    dates = [c["date"] for c in candles]
    times = [c["time"] for c in candles]
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    n = len(candles)

    trades = []
    in_position = False
    entry_price = 0.0
    entry_date = ""
    entry_time = None
    entry_idx = 0

    # Ensure stop_loss_pct is positive for comparison
    sl_ratio = abs(float(stop_loss_pct)) / 100.0 if stop_loss_pct else 0.07
    tp_ratio = abs(float(take_profit_pct)) / 100.0 if take_profit_pct else 0.0

    # Taiwan transaction cost: 0.1425% buy fee, 0.1425% sell fee + 0.3% tax
    BUY_FEE_RATE = 0.001425 if include_costs else 0.0
    SELL_FEE_AND_TAX = (0.001425 + 0.003) if include_costs else 0.0

    # Helper maps
    kd = indicators.get("kd", {})
    k_map = {item["time"]: item["value"] for item in kd.get("k", [])}
    d_map = {item["time"]: item["value"] for item in kd.get("d", [])}

    ma = indicators.get("ma", {})
    ma5_map = {item["time"]: item["value"] for item in ma.get("ma5", [])}
    ma20_map = {item["time"]: item["value"] for item in ma.get("ma20", [])}

    bb = indicators.get("bollinger", {})
    bb_upper_map = {item["time"]: item["value"] for item in bb.get("upper", [])}
    bb_lower_map = {item["time"]: item["value"] for item in bb.get("lower", [])}

    macd = indicators.get("macd", {})
    macd_bar_map = {item["time"]: item["value"] for item in macd.get("bar", [])}

    # Tracking equity over time
    equity_points = []
    current_cash_equity = 1.0
    initial_close = closes[0] if closes[0] > 0 else 1.0

    for i in range(1, n):
        t = times[i]
        t_prev = times[i-1]
        c = closes[i]
        h = highs[i]
        l = lows[i]

        buy_signal = False
        sell_signal = False
        sell_reason = ""

        # Check Entry Conditions if not in position
        if not in_position:
            if strategy == "kd_cross":
                k_now = k_map.get(t)
                d_now = d_map.get(t)
                k_prev = k_map.get(t_prev)
                d_prev = d_map.get(t_prev)
                if k_now is not None and d_now is not None and k_prev is not None and d_prev is not None:
                    if k_prev <= d_prev and k_now > d_now and k_now < 40:
                        buy_signal = True

            elif strategy == "ma_cross":
                m5_now = ma5_map.get(t)
                m20_now = ma20_map.get(t)
                m5_prev = ma5_map.get(t_prev)
                m20_prev = ma20_map.get(t_prev)
                if m5_now is not None and m20_now is not None and m5_prev is not None and m20_prev is not None:
                    if m5_prev <= m20_prev and m5_now > m20_now:
                        buy_signal = True

            elif strategy == "bb_rebound":
                low_v = bb_lower_map.get(t)
                if low_v is not None and l <= low_v and c >= candles[i]["open"]:
                    buy_signal = True

            elif strategy == "macd_turn_positive":
                b_now = macd_bar_map.get(t)
                b_prev = macd_bar_map.get(t_prev)
                if b_now is not None and b_prev is not None:
                    if b_prev <= 0 and b_now > 0:
                        buy_signal = True

            if buy_signal:
                in_position = True
                entry_price = c
                entry_date = dates[i]
                entry_time = t
                entry_idx = i

        # Check Exit Conditions if in position
        elif in_position:
            # 1. Stop loss check
            loss_pct = (c - entry_price) / entry_price
            if sl_ratio > 0 and loss_pct <= -sl_ratio:
                sell_signal = True
                sell_reason = f"停損出場 (-{round(sl_ratio*100, 1)}%)"

            # 2. Take profit check
            elif tp_ratio > 0 and loss_pct >= tp_ratio:
                sell_signal = True
                sell_reason = f"達標停利 (+{round(tp_ratio*100, 1)}%)"

            # 3. Strategy Indicator Exit Rules
            elif strategy == "kd_cross":
                k_now = k_map.get(t)
                d_now = d_map.get(t)
                k_prev = k_map.get(t_prev)
                d_prev = d_map.get(t_prev)
                if k_now is not None and d_now is not None and k_prev is not None and d_prev is not None:
                    if k_prev >= d_prev and k_now < d_now and k_now > 65:
                        sell_signal = True
                        sell_reason = "高檔 KD 死叉出場"

            elif strategy == "ma_cross":
                m5_now = ma5_map.get(t)
                m20_now = ma20_map.get(t)
                m5_prev = ma5_map.get(t_prev)
                m20_prev = ma20_map.get(t_prev)
                if m5_now is not None and m20_now is not None and m5_prev is not None and m20_prev is not None:
                    if m5_prev >= m20_prev and m5_now < m20_now:
                        sell_signal = True
                        sell_reason = "5MA / 20MA 均線死叉出場"

            elif strategy == "bb_rebound":
                up_v = bb_upper_map.get(t)
                if up_v is not None and c >= up_v:
                    sell_signal = True
                    sell_reason = "觸及布林上軌停利出場"

            elif strategy == "macd_turn_positive":
                b_now = macd_bar_map.get(t)
                b_prev = macd_bar_map.get(t_prev)
                if b_now is not None and b_prev is not None and b_now < 0 and b_prev >= 0:
                    sell_signal = True
                    sell_reason = "MACD 柱狀體翻綠死叉出場"

            # Force close on last candle of backtest period
            if not sell_signal and i == n - 1:
                sell_signal = True
                sell_reason = "回測期滿平倉"

            if sell_signal:
                exit_price = c
                # Calculate Net PnL with Taiwan costs
                entry_cost = entry_price * (1.0 + BUY_FEE_RATE)
                exit_net = exit_price * (1.0 - SELL_FEE_AND_TAX)
                trade_multiplier = exit_net / entry_cost
                pnl_pct = round((trade_multiplier - 1.0) * 100, 2)

                trades.append({
                    "entryDate": entry_date,
                    "entryTime": entry_time,
                    "entryPrice": entry_price,
                    "exitDate": dates[i],
                    "exitTime": t,
                    "exitPrice": exit_price,
                    "holdingDays": i - entry_idx,
                    "pnlPct": pnl_pct,
                    "reason": sell_reason,
                    "isWin": pnl_pct > 0
                })

                current_cash_equity *= trade_multiplier
                in_position = False

        # Track daily equity for chart curve
        if in_position:
            unrealized_exit_net = c * (1.0 - SELL_FEE_AND_TAX)
            unrealized_entry_cost = entry_price * (1.0 + BUY_FEE_RATE)
            pos_multiplier = unrealized_exit_net / unrealized_entry_cost
            day_strat_eq = current_cash_equity * pos_multiplier
        else:
            day_strat_eq = current_cash_equity

        day_bnh_eq = c / initial_close

        if i % 2 == 0 or buy_signal or sell_signal or i == n - 1:
            equity_points.append({
                "date": dates[i].split(" ")[0],
                "time": t,
                "strategyReturn": round((day_strat_eq - 1.0) * 100, 2),
                "buyAndHoldReturn": round((day_bnh_eq - 1.0) * 100, 2)
            })

    # Summary Statistics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["pnlPct"] > 0]
    losing_trades = [t for t in trades if t["pnlPct"] <= 0]
    win_rate = round((len(winning_trades) / total_trades) * 100, 1) if total_trades > 0 else 0.0

    total_win_pct = sum(t["pnlPct"] for t in winning_trades)
    total_loss_pct = abs(sum(t["pnlPct"] for t in losing_trades))
    profit_factor = round(total_win_pct / total_loss_pct, 2) if total_loss_pct > 0 else (99.9 if total_win_pct > 0 else 0.0)

    strategy_return = round((current_cash_equity - 1.0) * 100, 2)
    buy_and_hold = round(((closes[-1] - closes[0]) / closes[0]) * 100, 2) if closes[0] > 0 else 0.0

    # Maximum Drawdown (MDD) calculation
    peak_eq = 1.0
    max_dd = 0.0
    for pt in equity_points:
        curr_eq = 1.0 + (pt["strategyReturn"] / 100.0)
        if curr_eq > peak_eq:
            peak_eq = curr_eq
        if peak_eq > 0:
            dd = (peak_eq - curr_eq) / peak_eq
            if dd > max_dd:
                max_dd = dd
    mdd_pct = round(max_dd * 100, 2)

    # Average holding days
    avg_holding = round(sum(t["holdingDays"] for t in trades) / total_trades, 1) if total_trades > 0 else 0.0

    # Chart Markers for Lightweight Charts
    markers = []
    for t in trades:
        # Buy marker
        markers.append({
            "time": t["entryTime"],
            "position": "belowBar",
            "color": "#ff4d4f",
            "shape": "arrowUp",
            "text": f"買 {round(t['entryPrice'], 1)}"
        })
        # Sell marker
        is_win = t["pnlPct"] > 0
        markers.append({
            "time": t["exitTime"],
            "position": "aboveBar",
            "color": "#00b96b" if is_win else "#8c8c8c",
            "shape": "arrowDown",
            "text": f"{'獲利' if is_win else '停損'} {t['pnlPct']:+.1f}%"
        })

    return {
        "strategy": strategy,
        "strategyReturn": strategy_return,
        "buyAndHoldReturn": buy_and_hold,
        "totalTrades": total_trades,
        "winRate": win_rate,
        "winningTradesCount": len(winning_trades),
        "losingTradesCount": len(losing_trades),
        "profitFactor": profit_factor,
        "maxDrawdown": mdd_pct,
        "avgHoldingDays": avg_holding,
        "includeCosts": include_costs,
        "stopLossPct": round(sl_ratio * 100, 1),
        "takeProfitPct": round(tp_ratio * 100, 1),
        "equityCurve": equity_points,
        "markers": markers,
        "trades": trades[-12:]
    }

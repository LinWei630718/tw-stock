/**
 * Technical Strategy Backtest UI Module
 * Supports customizable stop-loss, take-profit, transaction costs,
 * SVG equity curve visualization, and chart buy/sell markers.
 */

class BacktestUI {
  constructor(containerId, onMarkersCallback = null) {
    this.container = document.getElementById(containerId);
    this.onMarkersCallback = onMarkersCallback;
    this.currentCode = "2330";
    this.lastResult = null;
    this.showMarkersOnChart = true;
    this.renderBase();
  }

  setStock(code) {
    this.currentCode = code;
    this.runBacktest();
  }

  renderBase() {
    this.container.innerHTML = `
      <!-- Strategy Selector & Execute -->
      <div style="margin-bottom:12px;">
        <label style="font-size:11px; font-weight:700; color:var(--text-muted); display:block; margin-bottom:4px;">🎯 選擇回測策略</label>
        <div style="display:flex; gap:6px;">
          <select id="backtest-strategy-select" style="flex:1; background:var(--bg-card); border:1px solid var(--border-color); color:var(--text-primary); padding:7px 10px; border-radius:8px; font-size:12px; outline:none;">
            <option value="kd_cross">⚡ KD 20/80 超買超賣波段策略</option>
            <option value="ma_cross">📈 5MA / 20MA 雙均線黃金交叉策略</option>
            <option value="bb_rebound">🎯 布林通道下軌反彈波段策略</option>
            <option value="macd_turn_positive">🌊 MACD 柱狀體翻紅進場策略</option>
          </select>
          <button id="run-backtest-btn" style="background:var(--color-accent); color:#0b0e14; border:none; padding:7px 14px; border-radius:8px; font-size:12px; font-weight:800; cursor:pointer; transition:all 0.2s;">
            執行回測
          </button>
        </div>
      </div>

      <!-- Risk & Cost Controls (Collapsible/Inline) -->
      <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:8px; padding:10px; margin-bottom:12px;">
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
          <div>
            <label style="font-size:11px; color:var(--text-secondary); display:block; margin-bottom:3px;">🛑 停損比例</label>
            <select id="backtest-stoploss-select" style="width:100%; background:var(--bg-secondary); border:1px solid var(--border-color); color:var(--text-primary); padding:5px 8px; border-radius:6px; font-size:11px; outline:none;">
              <option value="3">-3% 嚴格停損</option>
              <option value="5">-5% 標準停損</option>
              <option value="7" selected>-7% 寬幅停損 (預設)</option>
              <option value="10">-10% 深度防守</option>
              <option value="0">不設停損</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px; color:var(--text-secondary); display:block; margin-bottom:3px;">🎯 停利比例</label>
            <select id="backtest-takeprofit-select" style="width:100%; background:var(--bg-secondary); border:1px solid var(--border-color); color:var(--text-primary); padding:5px 8px; border-radius:6px; font-size:11px; outline:none;">
              <option value="8">+8% 短線獲利</option>
              <option value="12">+12% 波段獲利</option>
              <option value="15" selected">+15% 標準目標 (預設)</option>
              <option value="25">+25% 長線波段</option>
              <option value="0">不設限 (隨指標出場)</option>
            </select>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; pt:4px; border-top:1px solid rgba(255,255,255,0.04); padding-top:6px;">
          <label style="font-size:11px; color:var(--text-muted); display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="backtest-costs-checkbox" checked style="accent-color:var(--color-accent);">
            <span>扣除台股手續費(0.1425%)與證交稅(0.3%)</span>
          </label>
          <label style="font-size:11px; color:var(--text-muted); display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="backtest-markers-checkbox" checked style="accent-color:var(--color-accent);">
            <span>主圖買賣點標記</span>
          </label>
        </div>
      </div>

      <!-- Backtest Results Area -->
      <div id="backtest-results-area">
        <div style="text-align:center; padding:20px; color:var(--text-muted); font-size:12px;">
          請點擊「執行回測」以計算歷史績效
        </div>
      </div>
    `;

    document.getElementById("run-backtest-btn").addEventListener("click", () => this.runBacktest());
    document.getElementById("backtest-strategy-select").addEventListener("change", () => this.runBacktest());
    document.getElementById("backtest-stoploss-select").addEventListener("change", () => this.runBacktest());
    document.getElementById("backtest-takeprofit-select").addEventListener("change", () => this.runBacktest());
    document.getElementById("backtest-costs-checkbox").addEventListener("change", () => this.runBacktest());
    
    document.getElementById("backtest-markers-checkbox").addEventListener("change", (e) => {
      this.showMarkersOnChart = e.target.checked;
      if (this.onMarkersCallback) {
        if (this.showMarkersOnChart && this.lastResult && this.lastResult.markers) {
          this.onMarkersCallback(this.lastResult.markers);
        } else {
          this.onMarkersCallback([]);
        }
      }
    });
  }

  async runBacktest() {
    const area = document.getElementById("backtest-results-area");
    const strategySelect = document.getElementById("backtest-strategy-select");
    const stopLossSelect = document.getElementById("backtest-stoploss-select");
    const takeProfitSelect = document.getElementById("backtest-takeprofit-select");
    const costsCheckbox = document.getElementById("backtest-costs-checkbox");
    if (!area || !strategySelect) return;

    const strategy = strategySelect.value;
    const stopLoss = stopLossSelect ? parseFloat(stopLossSelect.value) : 7.0;
    const takeProfit = takeProfitSelect ? parseFloat(takeProfitSelect.value) : 15.0;
    const includeCosts = costsCheckbox ? costsCheckbox.checked : true;

    area.innerHTML = `
      <div style="text-align:center; padding:30px; color:var(--color-accent); font-size:12px; display:flex; align-items:center; justify-content:center; gap:8px;">
        <div class="spinner" style="width:18px; height:18px; border-width:2px;"></div>
        正在進行台股歷史回測 (納入成本與淨值試算)...
      </div>
    `;

    try {
      const res = await API.runBacktest(this.currentCode, strategy, "2y", stopLoss, takeProfit, includeCosts);
      const b = res.backtest;
      this.lastResult = b;

      if (!b || b.error) {
        area.innerHTML = `<div style="color:var(--color-up); font-size:12px; padding:15px;">${b?.error || "回測計算失敗"}</div>`;
        return;
      }

      // Sync markers to chart if enabled
      if (this.onMarkersCallback) {
        if (this.showMarkersOnChart && b.markers) {
          this.onMarkersCallback(b.markers);
        } else {
          this.onMarkersCallback([]);
        }
      }

      const stratRet = b.strategyReturn;
      const bnHRet = b.buyAndHoldReturn;
      const isStratPositive = stratRet >= 0;
      const stratColor = isStratPositive ? "up-text" : "down-text";
      const bnHColor = bnHRet >= 0 ? "up-text" : "down-text";

      // Build Trades Table rows
      let tradesHtml = "";
      if (b.trades && b.trades.length > 0) {
        b.trades.forEach(t => {
          const isWin = t.pnlPct >= 0;
          const pnlColor = isWin ? "up-text" : "down-text";
          tradesHtml += `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.03); font-size:11px;">
              <td style="padding:6px 4px; color:var(--text-secondary);">${t.entryDate.split(' ')[0]}</td>
              <td style="padding:6px 4px; color:var(--text-secondary);">${t.exitDate.split(' ')[0]}</td>
              <td style="padding:6px 4px; font-family:var(--font-mono);">${t.holdingDays}天</td>
              <td style="padding:6px 4px; font-size:10px; color:var(--text-muted);">${t.reason}</td>
              <td class="${pnlColor}" style="padding:6px 4px; font-family:var(--font-mono); font-weight:700; text-align:right;">
                ${t.pnlPct >= 0 ? '+' : ''}${t.pnlPct}%
              </td>
            </tr>
          `;
        });
      } else {
        tradesHtml = `<tr><td colspan="5" style="text-align:center; padding:15px; color:var(--text-muted);">期間內無觸發進出場交易</td></tr>`;
      }

      // Generate SVG Equity Curve
      const equitySvgHtml = this.generateEquityCurveSvg(b.equityCurve);

      area.innerHTML = `
        <!-- Metrics 4-Grid -->
        <div class="backtest-stat-grid">
          <div class="stat-box">
            <div class="stat-title">策略累積淨報酬</div>
            <div class="stat-val ${stratColor}">${stratRet >= 0 ? '+' : ''}${stratRet}%</div>
          </div>
          <div class="stat-box">
            <div class="stat-title">買進持有 (B&H)</div>
            <div class="stat-val ${bnHColor}">${bnHRet >= 0 ? '+' : ''}${bnHRet}%</div>
          </div>
          <div class="stat-box">
            <div class="stat-title">勝率 (獲利/總次)</div>
            <div class="stat-val" style="color:var(--color-accent);">${b.winRate}% <span style="font-size:10px; color:var(--text-muted);">(${b.winningTradesCount}/${b.totalTrades})</span></div>
          </div>
          <div class="stat-box">
            <div class="stat-title">最大回撤 (MDD)</div>
            <div class="stat-val" style="color:#fa8c16;">-${b.maxDrawdown}%</div>
          </div>
        </div>

        <!-- Profit Factor & Holding Days -->
        <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin: 6px 2px 10px 2px;">
          <span>獲利因子: <strong style="color:var(--text-primary); font-family:var(--font-mono);">${b.profitFactor}</strong></span>
          <span>平均持倉天數: <strong style="color:var(--text-primary); font-family:var(--font-mono);">${b.avgHoldingDays} 天</strong></span>
          <span>交易成本: <strong style="color:${b.includeCosts ? '#52c41a' : '#faad14'};">${b.includeCosts ? '已扣除' : '未計入'}</strong></span>
        </div>

        <!-- Equity Curve Chart -->
        <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:10px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; font-size:11px;">
            <span style="font-weight:700; color:var(--text-primary);">📈 累積淨值走勢 (Equity Curve)</span>
            <div style="display:flex; gap:10px; font-size:10px;">
              <span style="color:var(--color-accent); font-weight:700;">● 策略淨值</span>
              <span style="color:#64748b;">┄ 買進持有</span>
            </div>
          </div>
          <div style="width:100%; overflow:hidden;">
            ${equitySvgHtml}
          </div>
        </div>

        <!-- Trade List -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin:10px 0 6px 0;">
          <div style="font-size:12px; font-weight:700; color:var(--text-secondary);">
            近期交易明細記錄 (近 12 筆)
          </div>
          <span style="font-size:10px; color:var(--text-muted);">已同步於主圖標記買賣點</span>
        </div>
        <table style="width:100%; border-collapse:collapse;">
          <thead>
            <tr style="border-bottom:1px solid var(--border-color); font-size:11px; color:var(--text-muted); text-align:left;">
              <th style="padding:4px;">進場</th>
              <th style="padding:4px;">出場</th>
              <th style="padding:4px;">天數</th>
              <th style="padding:4px;">原因</th>
              <th style="padding:4px; text-align:right;">損益</th>
            </tr>
          </thead>
          <tbody>
            ${tradesHtml}
          </tbody>
        </table>
      `;

    } catch (err) {
      area.innerHTML = `<div style="color:var(--color-up); font-size:12px; padding:15px;">回測錯誤: ${err.message}</div>`;
    }
  }

  generateEquityCurveSvg(points) {
    if (!points || points.length < 2) {
      return `<div style="text-align:center; padding:15px; color:var(--text-muted); font-size:11px;">資料點不足以繪製淨值曲線</div>`;
    }

    const w = 340;
    const h = 110;
    const padX = 15;
    const padY = 12;

    const sVals = points.map(p => p.strategyReturn);
    const bVals = points.map(p => p.buyAndHoldReturn);
    const allVals = [...sVals, ...bVals, 0];

    const minV = Math.min(...allVals);
    const maxV = Math.max(...allVals);
    const range = (maxV - minV) || 1;

    const getX = (idx) => (padX + (idx / (points.length - 1)) * (w - padX * 2)).toFixed(1);
    const getY = (val) => (h - padY - ((val - minV) / range) * (h - padY * 2)).toFixed(1);

    // Zero baseline Y
    const zeroY = getY(0);

    // Generate paths
    const sPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.strategyReturn)}`).join(' ');
    const bPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.buyAndHoldReturn)}`).join(' ');

    return `
      <svg viewBox="0 0 ${w} ${h}" style="width:100%; height:auto; display:block; overflow:visible;">
        <defs>
          <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--color-accent)" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="var(--color-accent)" stop-opacity="0.0"/>
          </linearGradient>
        </defs>

        <!-- 0% Baseline -->
        <line x1="${padX}" y1="${zeroY}" x2="${w - padX}" y2="${zeroY}" stroke="rgba(255,255,255,0.15)" stroke-dasharray="3 3" stroke-width="1"/>

        <!-- Buy & Hold Line -->
        <path d="${bPath}" fill="none" stroke="#64748b" stroke-width="1.2" stroke-dasharray="3 2"/>

        <!-- Strategy Line Area & Stroke -->
        <path d="${sPath} L ${getX(points.length - 1)} ${zeroY} L ${getX(0)} ${zeroY} Z" fill="url(#eqGrad)"/>
        <path d="${sPath}" fill="none" stroke="var(--color-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

        <!-- Start & End Points -->
        <circle cx="${getX(0)}" cy="${getY(points[0].strategyReturn)}" r="3" fill="var(--color-accent)"/>
        <circle cx="${getX(points.length - 1)}" cy="${getY(points[points.length - 1].strategyReturn)}" r="3.5" fill="#fff" stroke="var(--color-accent)" stroke-width="2"/>
      </svg>
    `;
  }
}


/**
 * Technical Screener UI Module
 * Handles strategy buttons, scanner execution, and result table click interactions
 */

class ScreenerUI {
  constructor(containerId, onSelectStock) {
    this.container = document.getElementById(containerId);
    this.onSelectStock = onSelectStock;
    this.currentStrategy = "kd_golden_cross";
    this.isLoading = false;

    this.renderBase();
  }

  renderBase() {
    this.container.innerHTML = `
      <div class="strategy-select-row">
        <button class="strategy-btn active" data-strategy="kd_golden_cross">⚡ 低檔KD金叉</button>
        <button class="strategy-btn" data-strategy="ma_bullish_breakout">📈 均線多頭突破</button>
        <button class="strategy-btn" data-strategy="bb_lower_rebound">🛡️ 布林下軌反彈</button>
        <button class="strategy-btn" data-strategy="macd_turn_positive">🌊 MACD紅柱初生</button>
        <button class="strategy-btn" data-strategy="volume_breakout">🚀 爆量長紅攻擊</button>
      </div>

      <div class="screener-results-box" id="screener-results-box">
        <div style="text-align:center; padding:30px; color:var(--text-muted); font-size:13px;">
          點擊上方技術策略即刻掃描台股熱門標的
        </div>
      </div>
    `;

    // Event listeners for strategy buttons
    const btns = this.container.querySelectorAll(".strategy-btn");
    btns.forEach(btn => {
      btn.addEventListener("click", () => {
        btns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentStrategy = btn.dataset.strategy;
        this.runScan(this.currentStrategy);
      });
    });

    this.hasScanned = false;
  }

  ensureScanned() {
    if (!this.hasScanned) {
      this.hasScanned = true;
      this.runScan(this.currentStrategy || "kd_golden_cross");
    }
  }

  async runScan(strategyId) {
    const resultsBox = document.getElementById("screener-results-box");
    if (!resultsBox) return;

    resultsBox.innerHTML = `
      <div style="text-align:center; padding:30px; color:var(--color-accent); font-size:13px; display:flex; align-items:center; justify-content:center; gap:10px;">
        <div class="spinner" style="width:20px; height:20px; border-width:2px;"></div>
        正在掃描台股核心候選池...
      </div>
    `;

    try {
      const data = await API.runScreener(strategyId);
      const matches = data.matches || [];

      if (matches.length === 0) {
        resultsBox.innerHTML = `
          <div style="text-align:center; padding:30px; color:var(--text-muted); font-size:13px;">
            此策略目前無完全符合之標的，市場正處於震盪整理階段。
          </div>
        `;
        return;
      }

      let rowsHtml = "";
      matches.forEach(item => {
        const isUp = item.change >= 0;
        const colorClass = isUp ? "up-text" : "down-text";
        const sign = isUp ? "+" : "";

        rowsHtml += `
          <tr class="screener-row" data-code="${item.code}">
            <td>
              <div style="font-weight:700; color:var(--text-primary);">${item.name}</div>
              <div style="font-size:10px; color:var(--text-muted); font-family:var(--font-mono);">${item.code}</div>
            </td>
            <td style="font-family:var(--font-mono); font-weight:700;">${item.price.toFixed(2)}</td>
            <td class="${colorClass}" style="font-family:var(--font-mono); font-weight:700;">
              ${sign}${item.changePercent.toFixed(2)}%
            </td>
            <td>
              <div style="font-size:11px; color:var(--color-accent); font-weight:600;">${item.matchReason}</div>
              <div style="font-size:10px; color:var(--text-muted);">${item.volumeLots} 張</div>
            </td>
          </tr>
        `;
      });

      resultsBox.innerHTML = `
        <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px; display:flex; justify-content:space-between;">
          <span>共篩選出 <b>${matches.length}</b> 檔符合標的</span>
          <span>點擊直接載入圖表</span>
        </div>
        <table class="screener-results-table">
          <thead>
            <tr>
              <th>股票</th>
              <th>現價</th>
              <th>漲跌幅</th>
              <th>策略特徵 / 成交量</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      `;

      // Bind row clicks
      resultsBox.querySelectorAll(".screener-row").forEach(row => {
        row.addEventListener("click", () => {
          const code = row.dataset.code;
          if (code && this.onSelectStock) {
            this.onSelectStock(code);
          }
        });
      });

    } catch (err) {
      resultsBox.innerHTML = `
        <div style="text-align:center; padding:20px; color:var(--color-up); font-size:12px;">
          掃描失敗: ${err.message}
        </div>
      `;
    }
  }
}

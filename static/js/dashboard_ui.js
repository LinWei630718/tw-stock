/**
 * Dashboard UI Module - Multi-Stock & Market Technical Overview
 * Focuses on MA5/MA20/MA60, MACD, and RSI across market bellwethers
 */

class DashboardUI {
  constructor(containerId, onSelectStock) {
    this.container = document.getElementById(containerId);
    this.onSelectStock = onSelectStock;
    this.isLoading = false;
  }

  async load() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:60px 20px; color:var(--color-accent); gap:12px;">
        <div class="spinner" style="width:36px; height:36px;"></div>
        <div style="font-size:14px; font-weight:600;">正在彙整台股多股 MA5/MA20/MA60、MACD 與 RSI 綜合數據...</div>
      </div>
    `;

    try {
      const data = await API.getDashboardSummary();
      this.render(data);
    } catch (err) {
      this.container.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--color-up);">
          Dashboard 載入失敗: ${err.message}
        </div>
      `;
    }
  }

  render(data) {
    if (!this.container) return;

    const temp = data.marketTemperature || 50;
    const mood = data.marketMood || "中立整理";
    const maRatio = data.bullishMaRatio || 0;
    const macdRatio = data.positiveMacdRatio || 0;
    const avgRsi = data.averageRsi || 50;
    const stocks = data.stocks || [];

    let moodColor = "#b0bec5";
    if (temp >= 70) moodColor = "#ff4d4f";
    else if (temp >= 55) moodColor = "#ff8a80";
    else if (temp <= 40) moodColor = "#00b96b";

    let stockCardsHtml = "";
    stocks.forEach(s => {
      const isUp = s.change >= 0;
      const colorClass = isUp ? "up-text" : "down-text";
      const sign = isUp ? "+" : "";

      // MA Status Badge
      let maBadgeClass = "badge-neutral";
      let maBadgeColor = "#94a3b8";
      if (s.ma.status === "bullish") {
        maBadgeClass = "badge-bull";
        maBadgeColor = "var(--color-up)";
      } else if (s.ma.status === "bearish") {
        maBadgeClass = "badge-bear";
        maBadgeColor = "var(--color-down)";
      } else if (s.ma.status === "above_ma20") {
        maBadgeClass = "badge-bull";
        maBadgeColor = "var(--color-accent)";
      }

      // MACD Status Badge
      const isMacdPos = s.macd.isPositive;
      const macdColor = isMacdPos ? "var(--color-up)" : "var(--color-down)";
      const macdText = isMacdPos ? `紅柱 (+${s.macd.bar.toFixed(2)})` : `綠柱 (${s.macd.bar.toFixed(2)})`;

      // RSI Status Badge
      let rsiColor = "var(--text-secondary)";
      let rsiStatusText = "中立區";
      if (s.rsi.status === "overbought") {
        rsiColor = "var(--color-up)";
        rsiStatusText = "超買警戒 (>75)";
      } else if (s.rsi.status === "oversold") {
        rsiColor = "var(--color-down)";
        rsiStatusText = "超賣醞釀 (<25)";
      }

      stockCardsHtml += `
        <div class="dash-stock-card" data-code="${s.code}">
          <div class="dash-card-header">
            <div>
              <div class="dash-stock-name">${s.name} <span class="dash-stock-code">${s.code}</span></div>
              <div style="font-size:11px; color:var(--text-muted);">${s.market} · ${s.industry}</div>
            </div>
            <div class="dash-price-box">
              <div class="dash-price ${colorClass}">${s.price.toFixed(2)}</div>
              <div class="dash-change ${colorClass}">${sign}${s.change.toFixed(2)} (${sign}${s.changePercent.toFixed(2)}%)</div>
            </div>
          </div>

          <!-- Indicator Checklist Table -->
          <div class="dash-card-indicators">
            <!-- MA5 / MA20 / MA60 -->
            <div class="dash-ind-row">
              <span class="dash-ind-label">均線排列 (MA5 / 20 / 60)</span>
              <span class="dash-ind-badge" style="color:${maBadgeColor}; border-color:${maBadgeColor}44; background:${maBadgeColor}11;">
                ${s.ma.label}
              </span>
            </div>
            <div class="dash-ma-pills">
              <span>MA5: <b>${s.ma.ma5 ? s.ma.ma5.toFixed(1) : '--'}</b></span>
              <span>MA20: <b>${s.ma.ma20 ? s.ma.ma20.toFixed(1) : '--'}</b></span>
              <span>MA60: <b>${s.ma.ma60 ? s.ma.ma60.toFixed(1) : '--'}</b></span>
            </div>

            <!-- MACD (12, 26, 9) -->
            <div class="dash-ind-row" style="margin-top:8px;">
              <span class="dash-ind-label">MACD 柱狀體 (OSC)</span>
              <span class="dash-ind-badge" style="color:${macdColor}; border-color:${macdColor}44; background:${macdColor}11;">
                ${macdText}
              </span>
            </div>
            <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono); margin-bottom:4px;">
              DIF: ${s.macd.dif.toFixed(2)} | DEA: ${s.macd.dea.toFixed(2)}
            </div>

            <!-- RSI (6) -->
            <div class="dash-ind-row" style="margin-top:6px;">
              <span class="dash-ind-label">RSI(6) 相對強弱</span>
              <span class="dash-ind-badge" style="color:${rsiColor}; border-color:${rsiColor}44; background:${rsiColor}11;">
                ${s.rsi.rsi6.toFixed(1)} · ${rsiStatusText}
              </span>
            </div>
          </div>

          <div class="dash-card-footer">
            <div style="display:flex; align-items:center; gap:8px;">
              <div class="dash-mini-score" style="border-color:${s.score >= 60 ? 'var(--color-up)' : 'var(--color-down)'};">
                ${s.score}
              </div>
              <div style="font-size:11px; font-weight:700; color:var(--text-secondary);">${s.rating}</div>
            </div>
            <button class="dash-view-chart-btn" data-code="${s.code}">進入深度 K 線圖 ›</button>
          </div>
        </div>
      `;
    });

    this.container.innerHTML = `
      <div class="dashboard-wrapper">
        <!-- Market Pulse Temperature Banner -->
        <div class="market-pulse-card">
          <div class="pulse-left">
            <div class="temp-gauge-circle" style="border-color:${moodColor}; box-shadow: 0 0 20px ${moodColor}33;">
              <div class="temp-gauge-val" style="color:${moodColor};">${temp}</div>
              <div class="temp-gauge-lbl">溫度指數</div>
            </div>
            <div>
              <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">台股多空技術溫度計</div>
              <div class="temp-mood-title" style="color:${moodColor};">${mood}</div>
              <div style="font-size:12px; color:var(--text-secondary); max-width:420px; line-height:1.4; margin-top:4px;">
                基於核心權值股 MA5/MA20/MA60 多空排列比重、MACD 紅綠柱動能及 RSI 綜合加權換算之市場技術指標。
              </div>
            </div>
          </div>

          <div class="pulse-metrics-grid">
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">均線多頭排列佔比</div>
              <div class="pulse-metric-val" style="color:var(--color-up);">${maRatio}%</div>
              <div style="font-size:10px; color:var(--text-muted);">MA5 > MA20 > MA60</div>
            </div>
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">MACD 正柱 (紅柱) 佔比</div>
              <div class="pulse-metric-val" style="color:var(--color-accent);">${macdRatio}%</div>
              <div style="font-size:10px; color:var(--text-muted);">多頭攻擊發動狀態</div>
            </div>
            <div class="pulse-metric-box">
              <div class="pulse-metric-label">核心標的平均 RSI(6)</div>
              <div class="pulse-metric-val">${avgRsi}</div>
              <div style="font-size:10px; color:var(--text-muted);">市場動能水位</div>
            </div>
          </div>
        </div>

        <!-- Dashboard Section Title -->
        <div class="dash-section-header">
          <div>
            <div style="font-size:16px; font-weight:700; color:var(--text-primary);">核心權值與熱門指標股技術矩陣</div>
            <div style="font-size:12px; color:var(--text-muted);">實時監控 MA5 / MA20 / MA60 均線排列、MACD 柱狀動能與 RSI 水位</div>
          </div>
          <button id="dash-refresh-btn" class="color-toggle-btn" style="font-size:12px; padding:5px 12px;">
            🔄 重新整理看板
          </button>
        </div>

        <!-- Stocks Grid Cards -->
        <div class="dash-stocks-grid">
          ${stockCardsHtml}
        </div>
      </div>
    `;

    // Bind card click & button events
    this.container.querySelectorAll(".dash-view-chart-btn, .dash-stock-card").forEach(el => {
      el.addEventListener("click", (e) => {
        const code = el.dataset.code || el.closest(".dash-stock-card").dataset.code;
        if (code && this.onSelectStock) {
          this.onSelectStock(code);
        }
      });
    });

    const refreshBtn = document.getElementById("dash-refresh-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.load());
    }
  }
}

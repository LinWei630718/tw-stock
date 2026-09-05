/**
 * Technical Diagnostic UI Module
 * Renders Score, 4-Dimension Progress Bars, and Buy/Sell/Caution Technical Signals
 */

class DiagnosticUI {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(diagnosisData) {
    if (!diagnosisData || !diagnosisData.diagnosis) {
      this.container.innerHTML = `<div style="color:var(--text-muted); padding:20px; text-align:center;">暫無診斷數據</div>`;
      return;
    }

    const d = diagnosisData.diagnosis;
    const score = d.score || 50;
    const rating = d.rating || "中立整理";
    const ratingColor = d.rating_color || "#b0bec5";
    const dims = d.dimensions || { trend: 50, momentum: 50, volume: 50, volatility: 50 };
    const signals = d.signals || [];

    // ETF Specific Radar Card if current stock is an ETF
    let etfRadarHtml = "";
    const etf = diagnosisData.summary ? diagnosisData.summary.etf : null;
    if (etf && etf.timing) {
      const t = etf.timing;
      const prem = etf.premiumDiscountPercent || 0;
      const pSign = prem > 0 ? "+" : "";
      const reasonsList = (t.reasons || []).map(r => `
        <div class="etf-reason-item">
          <span class="etf-reason-dot"></span>
          <span>${r}</span>
        </div>
      `).join("");

      etfRadarHtml = `
        <div class="etf-radar-card">
          <div class="etf-radar-header">
            <div class="etf-radar-title">
              <span>🎯</span>
              <span>ETF 進出時機雷達</span>
            </div>
            <div class="etf-action-badge" style="background:${t.actionColor}22; color:${t.actionColor}; border:1px solid ${t.actionColor};">
              <span>${t.action}</span>
            </div>
          </div>

          <div class="etf-grid-metrics">
            <div class="etf-metric-box">
              <div class="etf-metric-title">折溢價率</div>
              <div class="etf-metric-val" style="color:${prem < -0.4 ? '#52c41a' : (prem > 0.6 ? '#fa8c16' : '#1890ff')}">${pSign}${prem.toFixed(2)}%</div>
            </div>
            <div class="etf-metric-box">
              <div class="etf-metric-title">估計淨值 (NAV)</div>
              <div class="etf-metric-val" style="color:#b37feb">${etf.nav ? etf.nav.toFixed(2) : '--'} 元</div>
            </div>
            <div class="etf-metric-box">
              <div class="etf-metric-title">買賣價差 / 流動性</div>
              <div class="etf-metric-val" style="color:#13c2c2">${etf.spreadPercent !== null ? etf.spreadPercent + '%' : '--'}</div>
            </div>
          </div>

          <div class="etf-reasons-list">
            <div style="font-size:11px; font-weight:700; color:var(--text-muted); margin-bottom:2px;">時機研判核心依據 (折溢價 × 價差量能 × MACD/均線):</div>
            ${reasonsList}
          </div>
        </div>
      `;
    }

    // Diagnostic summary description
    let desc = "各項指標訊號平衡，建議觀察關鍵壓力支撐。";
    if (score >= 75) desc = "多頭排列明確，動能強勁且有量能配合，技術面維持強勢格局。";
    else if (score >= 60) desc = "短線走勢偏多，部分指標呈現多方突破訊號，注意逢拉回支撐。";
    else if (score <= 30) desc = "均線與動能指標偏空，賣壓尚未消化完畢，建議控制風險謹慎操作。";
    else if (score <= 45) desc = "短線動能偏弱，均線走平或下彎，建議等待轉折向上再行介入。";

    let signalsHtml = "";
    if (signals.length === 0) {
      signalsHtml = `<div style="font-size:12px; color:var(--text-muted); padding:10px 0;">目前無特殊技術異動訊號</div>`;
    } else {
      signals.forEach(s => {
        signalsHtml += `
          <div class="signal-item ${s.type}">
            <span class="signal-tag">${s.tag}</span>
            <span>${s.text}</span>
          </div>
        `;
      });
    }

    this.container.innerHTML = `
      ${etfRadarHtml}

      <!-- Score Circle Card -->
      <div class="score-card">
        <div class="score-circle" style="border-color: ${ratingColor}; box-shadow: 0 0 15px ${ratingColor}44;">
          <div class="score-number" style="color: ${ratingColor};">${score}</div>
          <div class="score-text-sub">綜合評分</div>
        </div>
        <div class="score-info">
          <div class="score-rating" style="color: ${ratingColor};">${rating}</div>
          <div class="score-desc">${desc}</div>
        </div>
      </div>

      <!-- 4 Dimensions Breakdown -->
      <div class="dimensions-card">
        <div class="signals-title">
          <span>📊</span>
          <span>四大多空維度評量</span>
        </div>

        <div class="dimension-row">
          <div class="dimension-labels">
            <span>趨勢強度 (MA 均線)</span>
            <span>${dims.trend} / 100</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${dims.trend}%;"></div>
          </div>
        </div>

        <div class="dimension-row">
          <div class="dimension-labels">
            <span>動能指標 (KD & MACD)</span>
            <span>${dims.momentum} / 100</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${dims.momentum}%;"></div>
          </div>
        </div>

        <div class="dimension-row">
          <div class="dimension-labels">
            <span>成交量能 (量價結構)</span>
            <span>${dims.volume} / 100</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${dims.volume}%;"></div>
          </div>
        </div>

        <div class="dimension-row">
          <div class="dimension-labels">
            <span>波動通道 (布林開口)</span>
            <span>${dims.volatility} / 100</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${dims.volatility}%;"></div>
          </div>
        </div>
      </div>

      <!-- Real-time Signals Checklist -->
      <div class="signals-card">
        <div class="signals-title">
          <span>🎯</span>
          <span>即時技術訊號偵測 (${signals.length})</span>
        </div>
        <div class="signals-list">
          ${signalsHtml}
        </div>
      </div>
    `;
  }
}
